from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pandas_ta as ta
from smartmoneyconcepts import smc

from .config import StrategyConfig


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str  # "buy_limit" | "sell_limit"
    entry: float
    sl: float
    tp: float
    context_note: str


class ZeroFadeStrategy:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @staticmethod
    def _pip_size(symbol: str) -> float:
        return 0.01 if symbol.endswith("JPY") else 0.0001

    @staticmethod
    def _nearest_double_zero(price: float, pip_size: float) -> float:
        # Double-zero level increments by 100 pips in 5-digit FX pricing.
        bucket_size: float = pip_size * 100
        return round(round(price / bucket_size) * bucket_size, 5)

    def _build_indicators(self, rates: pd.DataFrame) -> pd.DataFrame:
        frame: pd.DataFrame = rates.copy()
        frame["sma20"] = ta.sma(frame["close"], length=self.config.sma_length)

        ohlc: pd.DataFrame = frame[["open", "high", "low", "close"]].copy()
        swings: pd.DataFrame = smc.swing_highs_lows(ohlc, swing_length=25)
        frame["smc_swing_high"] = swings.get("HighLow", pd.Series(index=frame.index, dtype="float64"))
        return frame

    def generate_signal(self, symbol: str, rates: pd.DataFrame) -> Signal | None:
        frame: pd.DataFrame = self._build_indicators(rates=rates)
        latest: pd.Series = frame.iloc[-1]

        close_price: float = float(latest["close"])
        sma20: float = float(latest["sma20"])
        pip_size: float = self._pip_size(symbol=symbol)

        anchor: float = self._nearest_double_zero(price=close_price, pip_size=pip_size)
        entry_offset_pips: float = (self.config.entry_offset_pips_min + self.config.entry_offset_pips_max) / 2
        entry_offset: float = entry_offset_pips * pip_size

        if close_price < sma20:
            entry: float = anchor + entry_offset
            sl: float = anchor - (self.config.stop_offset_pips * pip_size)
            tp: float = entry + (self.config.take_profit_pips * pip_size)
            return Signal(
                symbol=symbol,
                side="buy_limit",
                entry=entry,
                sl=sl,
                tp=tp,
                context_note=f"Long trap at {anchor:.5f} below SMA20.",
            )

        if close_price > sma20:
            entry = anchor - entry_offset
            sl = anchor + (self.config.stop_offset_pips * pip_size)
            tp = entry - (self.config.take_profit_pips * pip_size)
            return Signal(
                symbol=symbol,
                side="sell_limit",
                entry=entry,
                sl=sl,
                tp=tp,
                context_note=f"Short trap at {anchor:.5f} above SMA20.",
            )

        return None
