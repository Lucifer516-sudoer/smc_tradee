from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import MetaTrader5 as mt5
import pandas as pd
from loguru import logger


@dataclass(frozen=True)
class PendingOrderRequest:
    symbol: str
    is_buy_limit: bool
    volume: float
    price: float
    sl: float
    tp: float
    comment: str


class MT5Gateway:
    def __init__(self, login: int, password: str, server: str) -> None:
        self.login = login
        self.password = password
        self.server = server

    def connect(self) -> None:
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
        logger.info("Connected to MetaTrader5 terminal.")

    def shutdown(self) -> None:
        mt5.shutdown()
        logger.info("MT5 shutdown complete.")

    def get_equity(self) -> float:
        account_info: Any = mt5.account_info()
        if account_info is None:
            raise RuntimeError(f"Unable to fetch account_info: {mt5.last_error()}")
        return float(account_info.equity)

    def get_rates(self, symbol: str, timeframe: int, bars: int) -> pd.DataFrame:
        rates: Any = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No rates for {symbol}: {mt5.last_error()}")

        frame: pd.DataFrame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame

    def has_open_or_pending_orders(self, symbol: str) -> bool:
        open_positions: Any = mt5.positions_get(symbol=symbol)
        pending_orders: Any = mt5.orders_get(symbol=symbol)
        return bool(open_positions) or bool(pending_orders)

    def place_pending_order(self, req: PendingOrderRequest) -> Any:
        order_type: int = mt5.ORDER_TYPE_BUY_LIMIT if req.is_buy_limit else mt5.ORDER_TYPE_SELL_LIMIT
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
        result: Any = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send returned None: {mt5.last_error()}")
        logger.info(f"OrderSend result for {req.symbol}: retcode={getattr(result, 'retcode', 'n/a')}.")
        return result


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


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")
