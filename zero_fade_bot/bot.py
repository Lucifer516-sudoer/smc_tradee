from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

from .config import BotConfig
from .mt5_gateway import MT5Gateway, PendingOrderRequest, mt5_timeframe_from_name, round_to_digits
from .news_filter import EconomicCalendarFilter, utc_now
from .strategy import Signal, ZeroFadeStrategy


@dataclass
class RuntimeState:
    kill_switch_triggered: bool = False


class ZeroFadeBot:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.gateway = MT5Gateway(
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
        )
        self.strategy = ZeroFadeStrategy(config=config.strategy)
        self.calendar_filter = EconomicCalendarFilter()
        self.state = RuntimeState()

    def _enforce_kill_switch(self) -> None:
        equity: float = self.gateway.get_equity()
        if equity < self.config.risk.kill_switch_equity_usd:
            self.state.kill_switch_triggered = True
            raise SystemExit(
                f"Kill switch triggered. Equity={equity:.2f} < {self.config.risk.kill_switch_equity_usd:.2f}"
            )

    def _submit_signal(self, signal: Signal) -> None:
        digits: int = 3 if signal.symbol.endswith("JPY") else 5
        request = PendingOrderRequest(
            symbol=signal.symbol,
            is_buy_limit=signal.side == "buy_limit",
            volume=self.config.risk.lot_size,
            price=round_to_digits(signal.entry, digits),
            sl=round_to_digits(signal.sl, digits),
            tp=round_to_digits(signal.tp, digits),
            comment="ZeroFade_Auto",
        )
        self.gateway.place_pending_order(req=request)
        logger.info(f"Submitted {signal.side} for {signal.symbol}. {signal.context_note}")

    def _scan_symbol(self, symbol: str) -> None:
        if self.calendar_filter.is_news_blackout(symbol=symbol, now_utc=utc_now()):
            return
        if self.gateway.has_open_or_pending_orders(symbol=symbol):
            logger.info(f"{symbol}: skipping; existing order/position found.")
            return

        timeframe: int = mt5_timeframe_from_name(self.config.strategy.timeframe_name)
        rates = self.gateway.get_rates(symbol=symbol, timeframe=timeframe, bars=self.config.strategy.bars_for_context)
        signal = self.strategy.generate_signal(symbol=symbol, rates=rates)

        if signal is None:
            logger.info(f"{symbol}: no valid setup.")
            return
        self._submit_signal(signal=signal)

    def run(self) -> None:
        self.gateway.connect()
        try:
            logger.info("Zero-Fade bot started.")
            logger.info(
                f"Risk profile => lot={self.config.risk.lot_size:.2f}, "
                f"kill_switch={self.config.risk.kill_switch_equity_usd:.2f}"
            )
            while not self.state.kill_switch_triggered:
                self._enforce_kill_switch()
                for symbol in self.config.strategy.major_pairs:
                    self._scan_symbol(symbol=symbol)
                time.sleep(self.config.poll_interval_seconds)
        finally:
            self.gateway.shutdown()
