from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class RiskConfig:
    initial_equity_usd: float = 10.0
    kill_switch_equity_usd: float = 4.0
    lot_size: float = 0.01
    per_trade_risk_usd: float = 2.0


@dataclass(frozen=True)
class StrategyConfig:
    timeframe_name: str = "M15"
    bars_for_context: int = 250
    sma_length: int = 20
    entry_offset_pips_min: float = 10.0
    entry_offset_pips_max: float = 15.0
    stop_offset_pips: float = 20.0
    take_profit_pips: float = 35.0
    major_pairs: Sequence[str] = field(
        default_factory=lambda: ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD")
    )


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file_path: Path = Path("logs/zero_fade.log")
    rotation: str = "10 MB"
    retention: str = "14 days"


@dataclass(frozen=True)
class BotConfig:
    mt5_login: int
    mt5_password: str
    mt5_server: str
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    poll_interval_seconds: int = 10
