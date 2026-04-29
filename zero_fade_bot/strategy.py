from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd
import pandas_ta as ta
from smartmoneyconcepts import smc

from .config import StrategyConfig
from .symbols import pip_size


class MarketRegime(Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str  # "buy_limit" | "sell_limit"
    entry: float
    sl: float
    tp: float
    context_note: str
    regime: MarketRegime = MarketRegime.UNKNOWN
    atr_sl_multiplier: float = 1.0


class ZeroFadeStrategy:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @staticmethod
    def _pip_size(symbol: str) -> float:
        return pip_size(symbol)

    @staticmethod
    def _nearest_double_zero(price: float, pip_size: float) -> float:
        # Double-zero level increments by 100 pips in 5-digit FX pricing.
        bucket_size: float = pip_size * 100
        return round(round(price / bucket_size) * bucket_size, 5)

    def _detect_regime(self, frame: pd.DataFrame) -> MarketRegime:
        """Detect market regime using EMA alignment and volatility."""
        if len(frame) < 50:
            return MarketRegime.UNKNOWN

        # Calculate EMAs for trend detection
        ema20 = ta.ema(frame["close"], length=20)
        ema50 = ta.ema(frame["close"], length=50)
        ema200 = ta.ema(frame["close"], length=200)

        # Calculate ATR for volatility
        atr = ta.atr(frame["high"], frame["low"], frame["close"], length=14)
        atr_pct = atr / frame["close"] * 100

        latest = frame.iloc[-1]
        prev10 = frame.iloc[-11] if len(frame) > 10 else frame.iloc[0]

        # EMA alignment check - all EMAs in order indicates trend
        e20_curr = float(ema20.iloc[-1]) if not pd.isna(ema20.iloc[-1]) else 0
        e50_curr = float(ema50.iloc[-1]) if not pd.isna(ema50.iloc[-1]) else 0
        e200_curr = float(ema200.iloc[-1]) if not pd.isna(ema200.iloc[-1]) else 0

        # Bullish alignment: EMA20 > EMA50 > EMA200
        bullish_alignment = e20_curr > e50_curr > e200_curr
        # Bearish alignment: EMA20 < EMA50 < EMA200
        bearish_alignment = e20_curr < e50_curr < e200_curr

        # Price position relative to EMAs
        price = float(latest["close"])
        price_vs_ema20 = price > e20_curr if e20_curr else False

        # ATR volatility check - high volatility often in trending markets
        avg_atr_pct = atr_pct.mean()
        current_atr_pct = (
            float(atr_pct.iloc[-1]) if not pd.isna(atr_pct.iloc[-1]) else 0
        )

        # Strong trend: EMA aligned + high ATR
        if (
            bullish_alignment or bearish_alignment
        ) and current_atr_pct > avg_atr_pct * 1.1:
            return MarketRegime.TRENDING

        # Ranging: EMA not aligned or low volatility
        if not (bullish_alignment or bearish_alignment):
            return MarketRegime.RANGING

        # Check for consolidation (low volatility range)
        if current_atr_pct < avg_atr_pct * 0.8:
            return MarketRegime.RANGING

        return MarketRegime.UNKNOWN

    def _calculate_atr_based_tp_sl(
        self, frame: pd.DataFrame, side: str
    ) -> tuple[float, float, float]:
        """Calculate dynamic TP/SL based on ATR."""
        atr = ta.atr(frame["high"], frame["low"], frame["close"], length=14)
        latest = frame.iloc[-1]
        atr_value = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0

        pip_size = self._pip_size(symbol="")
        close_price = float(latest["close"])

        # ATR in pips
        atr_pips = atr_value / pip_size

        # Dynamic SL based on ATR (1.5x ATR for stop)
        sl_atr_multiplier = self.config.sl_atr_multiplier  # Default 1.5
        sl_pips = max(atr_pips * sl_atr_multiplier, self.config.stop_offset_pips)

        # Dynamic TP based on ATR (2.5x ATR for target)
        tp_atr_multiplier = self.config.tp_atr_multiplier  # Default 2.5
        tp_pips = max(atr_pips * tp_atr_multiplier, self.config.take_profit_pips)

        # Ensure minimum RR of 1.5
        rr_target = self.config.min_rr
        if tp_pips < sl_pips * rr_target:
            tp_pips = sl_pips * rr_target

        if side == "buy":
            sl = close_price - (sl_pips * pip_size)
            tp = close_price + (tp_pips * pip_size)
        else:
            sl = close_price + (sl_pips * pip_size)
            tp = close_price - (tp_pips * pip_size)

        return tp, sl, sl_pips / (atr_pips if atr_pips > 0 else 1)

    def _build_indicators(self, rates: pd.DataFrame) -> pd.DataFrame:
        frame: pd.DataFrame = rates.copy()
        frame["sma20"] = ta.sma(frame["close"], length=self.config.sma_length)

        ohlc: pd.DataFrame = frame[["open", "high", "low", "close"]].copy()
        swings: pd.DataFrame = smc.swing_highs_lows(ohlc, swing_length=25)
        frame["smc_swing_high"] = swings.get(
            "HighLow", pd.Series(index=frame.index, dtype="float64")
        )
        return frame

    def generate_signal(self, symbol: str, rates: pd.DataFrame) -> Signal | None:
        frame: pd.DataFrame = self._build_indicators(rates=rates)
        latest: pd.Series = frame.iloc[-1]

        close_price: float = float(latest["close"])
        sma20: float = float(latest["sma20"])
        pip_size: float = self._pip_size(symbol=symbol)

        # === MARKET REGIME FILTER ===
        regime = self._detect_regime(frame)

        # Only trade in ranging markets (or unknown for safety)
        if regime == MarketRegime.TRENDING:
            return None  # Skip trades in strong trends

        # === ENTRY LEVEL CALCULATION ===
        anchor: float = self._nearest_double_zero(price=close_price, pip_size=pip_size)
        entry_offset_pips: float = (
            self.config.entry_offset_pips_min + self.config.entry_offset_pips_max
        ) / 2
        entry_offset: float = entry_offset_pips * pip_size

        # === DYNAMIC TP/SL (ATR-based) ===
        use_dynamic = getattr(self.config, "use_dynamic_tp_sl", True)

        if close_price < sma20:
            entry: float = anchor + entry_offset

            if use_dynamic:
                tp, sl, atr_mult = self._calculate_atr_based_tp_sl(frame, "buy")
            else:
                sl = anchor - (self.config.stop_offset_pips * pip_size)
                tp = entry + (self.config.take_profit_pips * pip_size)
                atr_mult = 1.0

            regime_note = f" [{regime.value}]" if regime != MarketRegime.UNKNOWN else ""
            return Signal(
                symbol=symbol,
                side="buy_limit",
                entry=entry,
                sl=sl,
                tp=tp,
                context_note=f"Long trap at {anchor:.5f} below SMA20.{regime_note}",
                regime=regime,
                atr_sl_multiplier=atr_mult,
            )

        if close_price > sma20:
            entry = anchor - entry_offset

            if use_dynamic:
                tp, sl, atr_mult = self._calculate_atr_based_tp_sl(frame, "sell")
            else:
                sl = anchor + (self.config.stop_offset_pips * pip_size)
                tp = entry - (self.config.take_profit_pips * pip_size)
                atr_mult = 1.0

            regime_note = f" [{regime.value}]" if regime != MarketRegime.UNKNOWN else ""
            return Signal(
                symbol=symbol,
                side="sell_limit",
                entry=entry,
                sl=sl,
                tp=tp,
                context_note=f"Short trap at {anchor:.5f} above SMA20.{regime_note}",
                regime=regime,
                atr_sl_multiplier=atr_mult,
            )

        return None
