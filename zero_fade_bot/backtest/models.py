from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    side: Side
    stop_loss_pips: float
    take_profit_pips: float


@dataclass
class Position:
    side: Side
    entry_time: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    # === NEW: Partial TP tracking ===
    partial_tp_triggered: bool = False
    partial_tp_price: float = 0.0
    use_partial_tp: bool = False
    partial_tp_rr: float = 1.0


@dataclass(frozen=True)
class FillEvent:
    time: datetime
    price: float
    slippage_pips: float
    spread_pips: float


@dataclass
class ClosedTrade:
    side: Side
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl: float
    rr: float
