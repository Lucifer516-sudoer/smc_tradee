from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import pandas as pd
import pandas_ta as ta
from smartmoneyconcepts import smc

from .models import Bar, Side, Signal
from ..symbols import pip_size


class MarketRegime(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    UNKNOWN = "unknown"


class BacktestStrategy(Protocol):
    def on_bar(self, bars: list[Bar], index: int) -> Signal | None: ...


@dataclass
class ZeroFadeBacktestStrategy:
    symbol: str
    sma_length: int = 20
    stop_loss_pips: float = 20.0
    take_profit_pips: float = 35.0
    # === NEW: Regime Filter ===
    use_regime_filter: bool = True
    # === NEW: Dynamic TP/SL ===
    use_dynamic_tp_sl: bool = True
    sl_atr_multiplier: float = 1.5
    tp_atr_multiplier: float = 2.5
    min_rr: float = 1.5
    # === NEW: Partial TP ===
    use_partial_tp: bool = True
    partial_tp_rr: float = 1.0

    _frame: pd.DataFrame = None

    def __post_init__(self):
        # This will be set when bars are first provided
        object.__setattr__(self, "_frame", None)

    def _pip_size(self) -> float:
        return pip_size(self.symbol)

    def _ensure_frame(self, bars: list[Bar]) -> pd.DataFrame:
        """Precompute indicators once for all bars."""
        if self._frame is None or len(self._frame) != len(bars):
            frame = pd.DataFrame(
                {
                    "open": [b.open for b in bars],
                    "high": [b.high for b in bars],
                    "low": [b.low for b in bars],
                    "close": [b.close for b in bars],
                }
            )
            # Precompute indicators once
            frame["sma20"] = ta.sma(frame["close"], length=self.sma_length)
            frame["ema20"] = ta.ema(frame["close"], length=20)
            frame["ema50"] = ta.ema(frame["close"], length=50)
            frame["ema200"] = ta.ema(frame["close"], length=200)
            frame["atr"] = ta.atr(
                frame["high"], frame["low"], frame["close"], length=14
            )
            # Skip expensive SMC calculations for backtest speed
            object.__setattr__(self, "_frame", frame)
        return self._frame

    def _detect_regime(self, frame: pd.DataFrame, index: int) -> MarketRegime:
        """Detect market regime using EMA alignment and volatility."""
        if index < 50:
            return MarketRegime.UNKNOWN

        latest = frame.iloc[index]
        e20 = float(latest["ema20"]) if not pd.isna(latest["ema20"]) else 0
        e50 = float(latest["ema50"]) if not pd.isna(latest["ema50"]) else 0
        e200 = float(latest["ema200"]) if not pd.isna(latest["ema200"]) else 0

        # EMA alignment check
        bullish = e20 > e50 > e200
        bearish = e20 < e50 < e200

        # ATR volatility check
        atr = float(latest["atr"]) if not pd.isna(latest["atr"]) else 0
        close = float(latest["close"])
        atr_pct = (atr / close) * 100 if close > 0 else 0

        # Calculate average ATR percentage over recent bars
        recent_atr_pct = (
            frame["atr"].iloc[max(0, index - 20) : index + 1]
            / frame["close"].iloc[max(0, index - 20) : index + 1]
        ) * 100
        avg_atr_pct = recent_atr_pct.mean() if len(recent_atr_pct) > 0 else 0

        if (bullish or bearish) and atr_pct > avg_atr_pct * 1.1:
            return MarketRegime.TRENDING

        if not (bullish or bearish):
            return MarketRegime.RANGING

        if atr_pct < avg_atr_pct * 0.8:
            return MarketRegime.RANGING

        return MarketRegime.UNKNOWN

    def _calculate_dynamic_tp_sl(
        self, frame: pd.DataFrame, index: int, side: Side
    ) -> tuple[float, float]:
        """Calculate dynamic TP/SL based on ATR."""
        latest = frame.iloc[index]
        close = float(latest["close"])
        atr = float(latest["atr"]) if not pd.isna(latest["atr"]) else 0

        if not self.use_dynamic_tp_sl or atr == 0:
            return self.take_profit_pips, self.stop_loss_pips

        pip_size = self._pip_size()
        atr_pips = atr / pip_size

        # Dynamic SL based on ATR
        sl_pips = max(atr_pips * self.sl_atr_multiplier, self.stop_loss_pips)

        # Dynamic TP based on ATR
        tp_pips = max(atr_pips * self.tp_atr_multiplier, self.take_profit_pips)

        # Ensure minimum RR
        if tp_pips < sl_pips * self.min_rr:
            tp_pips = sl_pips * self.min_rr

        return tp_pips, sl_pips

    def on_bar(self, bars: list[Bar], index: int) -> Signal | None:
        if index < self.sma_length + 5:
            return None

        # Use precomputed frame
        frame = self._ensure_frame(bars)

        if index >= len(frame):
            return None

        latest = frame.iloc[index]
        close = float(latest["close"])
        sma = float(latest["sma20"])

        # === REGIME FILTER ===
        if self.use_regime_filter:
            regime = self._detect_regime(frame, index)
            if regime == MarketRegime.TRENDING:
                return None  # Skip trades in strong trends

        # === DYNAMIC TP/SL ===
        if close < sma:
            tp_pips, sl_pips = self._calculate_dynamic_tp_sl(frame, index, Side.BUY)
            return Signal(
                side=Side.BUY,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
            )
        if close > sma:
            tp_pips, sl_pips = self._calculate_dynamic_tp_sl(frame, index, Side.SELL)
            return Signal(
                side=Side.SELL,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
            )
        return None
