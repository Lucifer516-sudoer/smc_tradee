from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import BacktestConfig
from .data_loader import CsvDataLoader
from .engine import BacktestEngine
from .strategy import ZeroFadeBacktestStrategy


class BacktestService:
    def __init__(self) -> None:
        self.loader = CsvDataLoader()

    def run_zero_fade(
        self,
        csv_path: str | Path,
        config: BacktestConfig,
        progress_callback=None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        bars = self.loader.load(csv_path, start_date=start_date, end_date=end_date)
        strategy = ZeroFadeBacktestStrategy(symbol=config.symbol)
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(bars, progress_callback=progress_callback)
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
