from __future__ import annotations

import os
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
    # === NEW: Market Regime Filter ===
    use_regime_filter: bool = True  # Enable/disable regime filtering
    regime_ema_fast: int = 20  # Fast EMA for regime detection
    regime_ema_slow: int = 200  # Slow EMA for regime detection
    # === NEW: Dynamic TP/SL (ATR-based) ===
    use_dynamic_tp_sl: bool = True  # Enable ATR-based TP/SL
    sl_atr_multiplier: float = 1.5  # SL = ATR * multiplier
    tp_atr_multiplier: float = 2.5  # TP = ATR * multiplier
    min_rr: float = 1.5  # Minimum risk:reward ratio
    # === NEW: Partial Profit Taking ===
    use_partial_tp: bool = True  # Enable partial profit taking
    partial_tp_pct: float = 0.5  # Close 50% at first TP
    partial_tp_rr: float = 1.0  # First TP at 1R profit
    move_sl_to_be_after_partial: bool = True  # Move SL to breakeven
    major_pairs: Sequence[str] = field(
        default_factory=lambda: (
            "EURUSD.m",
            "GBPUSD.m",
            "USDJPY.m",
            "USDCHF.m",
            "AUDUSD.m",
            "USDCAD.m",
        )
    )


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file_path: Path = Path("logs/bot.log")


@dataclass(frozen=True)
class BotConfig:
    mt5_login: int
    mt5_password: str
    mt5_server: str
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    poll_interval_seconds: int = 10


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        if line.lower().startswith("export "):
            line = line[7:].strip()
            if "=" not in line:
                continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _clean_env_value(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value


def load_config_from_env(env_path: str | Path = ".env") -> BotConfig:
    load_dotenv(env_path)

    risk = RiskConfig(
        initial_equity_usd=_env_float(
            "INITIAL_EQUITY_USD", RiskConfig.initial_equity_usd
        ),
        kill_switch_equity_usd=_env_float(
            "KILL_SWITCH_EQUITY_USD", RiskConfig.kill_switch_equity_usd
        ),
        lot_size=_env_float("LOT_SIZE", RiskConfig.lot_size),
        per_trade_risk_usd=_env_float(
            "PER_TRADE_RISK_USD", RiskConfig.per_trade_risk_usd
        ),
    )
    strategy = StrategyConfig(
        timeframe_name=_env_str("TIMEFRAME_NAME", StrategyConfig.timeframe_name),
        bars_for_context=_env_int("BARS_FOR_CONTEXT", StrategyConfig.bars_for_context),
        sma_length=_env_int("SMA_LENGTH", StrategyConfig.sma_length),
        entry_offset_pips_min=_env_float(
            "ENTRY_OFFSET_PIPS_MIN", StrategyConfig.entry_offset_pips_min
        ),
        entry_offset_pips_max=_env_float(
            "ENTRY_OFFSET_PIPS_MAX", StrategyConfig.entry_offset_pips_max
        ),
        stop_offset_pips=_env_float(
            "STOP_OFFSET_PIPS", StrategyConfig.stop_offset_pips
        ),
        take_profit_pips=_env_float(
            "TAKE_PROFIT_PIPS", StrategyConfig.take_profit_pips
        ),
        major_pairs=_env_sequence("MAJOR_PAIRS", StrategyConfig().major_pairs),
    )
    logging = LoggingConfig(
        level=_env_str("LOG_LEVEL", LoggingConfig.level),
        file_path=Path(_env_str("LOG_FILE_PATH", str(LoggingConfig.file_path))),
    )

    return BotConfig(
        mt5_login=_required_env_int("MT5_LOGIN"),
        mt5_password=_required_env("MT5_PASSWORD"),
        mt5_server=_required_env("MT5_SERVER"),
        risk=risk,
        strategy=strategy,
        logging=logging,
        poll_interval_seconds=_env_int(
            "POLL_INTERVAL_SECONDS", BotConfig.poll_interval_seconds
        ),
    )


def _clean_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _required_env(key: str) -> str:
    value = os.environ.get(key)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _required_env_int(key: str) -> int:
    return int(_required_env(key))


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    return default if value is None or value == "" else int(value)


def _env_float(key: str, default: float) -> float:
    value = os.environ.get(key)
    return default if value is None or value == "" else float(value)


def _env_sequence(key: str, default: Sequence[str]) -> Sequence[str]:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())
