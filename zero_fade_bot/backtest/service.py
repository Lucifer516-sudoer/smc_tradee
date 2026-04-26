from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import BacktestConfig
from .data_loader import CsvDataLoader
from .engine import BacktestEngine
from .strategy import ZeroFadeBacktestStrategy


class BacktestService:
    def __init__(self) -> None:
        self.loader = CsvDataLoader()

    def run_zero_fade(self, csv_path: str | Path, config: BacktestConfig) -> dict[str, Any]:
        bars = self.loader.load(csv_path)
        strategy = ZeroFadeBacktestStrategy(symbol=config.symbol)
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(bars)
        payload = asdict(result)
        payload["trades"] = [
            {
                **trade,
                "entry_time": trade["entry_time"].isoformat(),
                "exit_time": trade["exit_time"].isoformat(),
            }
            for trade in payload["trades"]
        ]
        return payload
