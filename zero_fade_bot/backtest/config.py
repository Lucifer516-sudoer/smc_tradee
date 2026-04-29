from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionConfig:
    spread_pips: float = 1.2
    slippage_pips: float = 0.5
    execution_delay_bars: int = 1


@dataclass(frozen=True)
class RiskConfig:
    initial_balance: float = 10.0
    lot_size: float = 0.01
    risk_percent_per_trade: float = 20.0
    pip_value_per_lot: float = 10.0


@dataclass(frozen=True)
class BacktestConfig:
    symbol: str
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
