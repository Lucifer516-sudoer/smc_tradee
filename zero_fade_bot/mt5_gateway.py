from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import time
from typing import Any, cast

import metatrader5_wrapper as mt5
import pandas as pd
from pydantic import SecretStr

from metatrader5_wrapper import LoginCredential, MetaTrader5Client


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingOrderRequest:
    symbol: str
    is_buy_limit: bool
    volume: float
    price: float
    sl: float
    tp: float
    comment: str


@dataclass(frozen=True)
class OrderPlacementResult:
    accepted: bool
    retcode: int
    retcode_name: str
    comment: str
    raw: Any


class MT5Gateway:
    """Wrapper-backed MT5 gateway for live trading operations."""

    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        *,
        connection_retries: int = 3,
        order_retries: int = 3,
        retry_delay_seconds: float = 2.0,
    ) -> None:
        self.credentials = LoginCredential(
            login=login,
            password=SecretStr(password),
            server=server,
        )
        self.client = MetaTrader5Client(self.credentials)
        self.connection_retries = connection_retries
        self.order_retries = order_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.connected = False

    def connect(self) -> None:
        """Initialize the MT5 client with retry handling."""
        last_error: RuntimeError | None = None
        for attempt in range(1, self.connection_retries + 1):
            result = self.client.initialize()
            if not result.failed:
                self.connected = True
                logger.info("Connected to MetaTrader5 terminal on attempt %s.", attempt)
                return
            last_error = RuntimeError(result.describe_error())
            logger.error(
                "MT5 initialization failed on attempt %s/%s: %s",
                attempt,
                self.connection_retries,
                result.describe_error(),
            )
            if attempt < self.connection_retries:
                time.sleep(self.retry_delay_seconds)
        raise RuntimeError("MT5 initialization failed after retries") from last_error

    def shutdown(self) -> None:
        """Shutdown the MT5 client cleanly."""
        result = self.client.shutdown()
        if result.failed:
            logger.warning(
                "MT5 shutdown reported an error: %s", result.describe_error()
            )
        self.connected = False
        logger.info("MT5 shutdown complete.")

    def get_equity(self) -> float:
        """Return current account equity."""
        account_info = self.client.account_info().expect("Unable to fetch account_info")
        return float(account_info.equity)

    def get_rates(self, symbol: str, timeframe: int, bars: int) -> pd.DataFrame:
        """Fetch historical rates and validate the returned frame."""
        self._validate_symbol(symbol)
        self._validate_timeframe(timeframe)
        if bars <= 0:
            raise ValueError("bars must be greater than zero")

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars).expect(
            f"No rates for {symbol}"
        )
        if len(rates) == 0:
            raise RuntimeError(f"No rates for {symbol}: empty response")

        normalized_rates = [self._normalize_rate(rate) for rate in rates]
        frame: pd.DataFrame = pd.DataFrame.from_records(normalized_rates)
        required_columns = {"time", "open", "high", "low", "close"}
        missing_columns = required_columns.difference(frame.columns)
        if missing_columns:
            raise RuntimeError(
                f"Rates payload missing columns for {symbol}: {sorted(missing_columns)}"
            )
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)  # type: ignore[assignment]
        return frame

    def get_symbol_digits(self, symbol: str) -> int:
        """Return the configured price precision for a symbol."""
        info_result = self.client.symbol_info(symbol)
        if info_result.failed:
            self.client.symbol_select(symbol, True).expect(
                f"Unable to select symbol {symbol}"
            )
            info_result = self.client.symbol_info(symbol)
        info = info_result.expect(f"Unable to fetch symbol_info for {symbol}")
        digits = getattr(info, "digits", None)
        if digits is None:
            raise RuntimeError(f"symbol_info for {symbol} did not include digits")
        return int(digits)

    def has_open_or_pending_orders(self, symbol: str) -> bool:
        """Check whether the symbol already has an open or pending exposure."""
        open_positions = self.client.positions_get(symbol=symbol).expect(
            f"Unable to fetch positions for {symbol}"
        )
        pending_orders = mt5.orders_get(symbol=symbol).expect(
            f"Unable to fetch pending orders for {symbol}"
        )
        return bool(open_positions) or bool(pending_orders)

    def place_pending_order(self, req: PendingOrderRequest) -> OrderPlacementResult:
        """Validate and submit a pending order with retry handling."""
        self._ensure_connected()
        self._validate_request(req)
        if self.has_open_or_pending_orders(req.symbol):
            raise ValueError(f"{req.symbol}: existing open or pending trade detected")

        order_type: int = (
            mt5.ORDER_TYPE_BUY_LIMIT if req.is_buy_limit else mt5.ORDER_TYPE_SELL_LIMIT
        )
        filling: int = mt5.ORDER_FILLING_RETURN
        expiry: int = mt5.ORDER_TIME_GTC

        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": req.symbol,
            "volume": req.volume,
            "type": order_type,
            "price": req.price,
            "sl": req.sl,
            "tp": req.tp,
            "deviation": 10,
            "magic": 204857,
            "comment": req.comment,
            "type_time": expiry,
            "type_filling": filling,
        }
        self._validate_pending_price(req=req)
        check = mt5.order_check(request).expect(
            f"order_check returned no data for {req.symbol}"
        )
        check_retcode = int(getattr(check, "retcode", mt5.TRADE_RETCODE_ERROR))
        if check_retcode not in self._success_retcodes():
            return self._placement_result(raw=check, accepted=False)

        self._validate_margin(req=req)

        last_error: RuntimeError | None = None
        for attempt in range(1, self.order_retries + 1):
            try:
                result = mt5.order_send(request).expect("order_send returned no data")
                result_retcode = int(
                    getattr(result, "retcode", mt5.TRADE_RETCODE_ERROR)
                )
                placement = self._placement_result(
                    raw=result, accepted=result_retcode in self._success_retcodes()
                )
                log = logger.info if placement.accepted else logger.warning
                log(
                    "OrderSend result for %s on attempt %s/%s: retcode=%s (%s); comment=%r.",
                    req.symbol,
                    attempt,
                    self.order_retries,
                    placement.retcode,
                    placement.retcode_name,
                    placement.comment,
                )
                if placement.accepted or attempt == self.order_retries:
                    return placement
            except RuntimeError as exc:
                last_error = exc
                logger.error(
                    "Order placement failed for %s on attempt %s/%s: %s",
                    req.symbol,
                    attempt,
                    self.order_retries,
                    exc,
                )
            time.sleep(self.retry_delay_seconds)

        raise RuntimeError(
            f"Order placement failed for {req.symbol} after retries"
        ) from last_error

    def _validate_pending_price(self, req: PendingOrderRequest) -> None:
        """Ensure the pending order price is on the correct side of market."""
        tick = self.client.symbol_info_tick(req.symbol).expect(
            f"Unable to fetch tick for {req.symbol}"
        )
        reference_price = float(tick.ask if req.is_buy_limit else tick.bid)
        if req.is_buy_limit and req.price >= reference_price:
            raise ValueError(
                f"{req.symbol}: buy_limit price {req.price} must be below current ask {reference_price}"
            )
        if not req.is_buy_limit and req.price <= reference_price:
            raise ValueError(
                f"{req.symbol}: sell_limit price {req.price} must be above current bid {reference_price}"
            )

    def _ensure_connected(self) -> None:
        if not self.connected:
            raise RuntimeError("MT5 client is not connected")

    def _validate_symbol(self, symbol: str) -> None:
        if not symbol or not symbol.strip():
            raise ValueError("symbol must be a non-empty string")

    @staticmethod
    def _validate_timeframe(timeframe: int) -> None:
        supported = {
            mt5.TIMEFRAME_M1,
            mt5.TIMEFRAME_M5,
            mt5.TIMEFRAME_M15,
            mt5.TIMEFRAME_M30,
            mt5.TIMEFRAME_H1,
        }
        if timeframe not in supported:
            raise ValueError(f"Unsupported timeframe value: {timeframe}")

    def _validate_request(self, req: PendingOrderRequest) -> None:
        self._validate_symbol(req.symbol)
        if req.volume <= 0:
            raise ValueError(f"{req.symbol}: volume must be positive")
        if req.sl <= 0 or req.tp <= 0 or req.price <= 0:
            raise ValueError(
                f"{req.symbol}: price, stop loss, and take profit must be positive"
            )
        symbol_info = self.client.symbol_info(req.symbol).expect(
            f"Unable to fetch symbol_info for {req.symbol}"
        )
        min_volume = float(getattr(symbol_info, "volume_min", 0.0) or 0.0)
        max_volume = float(getattr(symbol_info, "volume_max", 0.0) or 0.0)
        step_volume = float(getattr(symbol_info, "volume_step", 0.0) or 0.0)
        if min_volume and req.volume < min_volume:
            raise ValueError(
                f"{req.symbol}: volume {req.volume} is below minimum {min_volume}"
            )
        if max_volume and req.volume > max_volume:
            raise ValueError(
                f"{req.symbol}: volume {req.volume} exceeds maximum {max_volume}"
            )
        if step_volume:
            steps = round(req.volume / step_volume)
            if abs((steps * step_volume) - req.volume) > 1e-9:
                raise ValueError(
                    f"{req.symbol}: volume {req.volume} does not align with step {step_volume}"
                )
        if req.is_buy_limit:
            if not (req.sl < req.price < req.tp):
                raise ValueError(f"{req.symbol}: buy limit requires SL < entry < TP")
        else:
            if not (req.tp < req.price < req.sl):
                raise ValueError(f"{req.symbol}: sell limit requires TP < entry < SL")

    def _validate_margin(self, req: PendingOrderRequest) -> None:
        tick = self.client.symbol_info_tick(req.symbol).expect(
            f"Unable to fetch tick for {req.symbol}"
        )
        action = mt5.ORDER_TYPE_BUY if req.is_buy_limit else mt5.ORDER_TYPE_SELL
        market_price = float(tick.ask if req.is_buy_limit else tick.bid)
        margin_required = mt5.order_calc_margin(
            action, req.symbol, req.volume, market_price
        ).expect(f"Unable to calculate margin for {req.symbol}")
        account_info = self.client.account_info().expect("Unable to fetch account_info")
        free_margin = float(account_info.margin_free)
        if margin_required > free_margin:
            raise ValueError(
                f"{req.symbol}: insufficient free margin {free_margin:.2f} for required {float(margin_required):.2f}"
            )

    @staticmethod
    def _normalize_rate(rate: Any) -> dict[str, Any]:
        if isinstance(rate, dict):
            return rate

        as_dict = getattr(rate, "_asdict", None)
        if callable(as_dict):
            return dict(as_dict())

        model_dump = getattr(rate, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped

        if hasattr(rate, "dtype") and hasattr(rate, "tolist"):
            field_names = getattr(rate.dtype, "names", None)
            values = rate.tolist()
            if field_names and isinstance(values, tuple):
                return dict(zip(field_names, values, strict=False))

        raise RuntimeError(f"Unsupported rate payload type: {type(rate).__name__}")

    @staticmethod
    def _success_retcodes() -> set[int]:
        return {
            0,
            mt5.TRADE_RETCODE_PLACED,
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_DONE_PARTIAL,
        }

    @staticmethod
    def _placement_result(raw: Any, accepted: bool) -> OrderPlacementResult:
        retcode = int(getattr(raw, "retcode", mt5.TRADE_RETCODE_ERROR))
        return OrderPlacementResult(
            accepted=accepted,
            retcode=retcode,
            retcode_name=trade_retcode_name(retcode),
            comment=str(getattr(raw, "comment", "")),
            raw=raw,
        )


def mt5_timeframe_from_name(name: str) -> int:
    mapping: dict[str, int] = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
    }
    if name not in mapping:
        raise ValueError(f"Unsupported timeframe: {name}")
    return mapping[name]


def round_to_digits(value: float, digits: int) -> float:
    return float(round(value, digits))


def trade_retcode_name(retcode: int) -> str:
    if retcode == 0:
        return "TRADE_CHECK_OK"
    for name in dir(mt5):
        if name.startswith("TRADE_RETCODE_") and getattr(mt5, name) == retcode:
            return name
    return "UNKNOWN_RETCODE"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
