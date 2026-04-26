from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd
import pandas_ta as ta
from smartmoneyconcepts import smc

from .models import Bar, Side, Signal


class BacktestStrategy(Protocol):
    def on_bar(self, bars: list[Bar], index: int) -> Signal | None:
        ...


@dataclass(frozen=True)
class ZeroFadeBacktestStrategy:
    symbol: str
    sma_length: int = 20
    stop_loss_pips: float = 20.0
    take_profit_pips: float = 35.0

    def _pip_size(self) -> float:
        return 0.01 if self.symbol.endswith("JPY") else 0.0001

    def on_bar(self, bars: list[Bar], index: int) -> Signal | None:
        if index < self.sma_length + 5:
            return None

        slice_bars = bars[: index + 1]
        frame = pd.DataFrame(
            {
                "open": [b.open for b in slice_bars],
                "high": [b.high for b in slice_bars],
                "low": [b.low for b in slice_bars],
                "close": [b.close for b in slice_bars],
            }
        )
        frame["sma20"] = ta.sma(frame["close"], length=self.sma_length)
        _ = smc.swing_highs_lows(frame[["open", "high", "low", "close"]], swing_length=20)

        latest = frame.iloc[-1]
        close = float(latest["close"])
        sma = float(latest["sma20"])

        if close < sma:
            return Signal(side=Side.BUY, stop_loss_pips=self.stop_loss_pips, take_profit_pips=self.take_profit_pips)
        if close > sma:
            return Signal(side=Side.SELL, stop_loss_pips=self.stop_loss_pips, take_profit_pips=self.take_profit_pips)
        return None
