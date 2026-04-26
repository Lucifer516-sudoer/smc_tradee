from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import Bar


class CsvDataLoader:
    """Loads ForexSB-style CSV into normalized bars."""

    REQUIRED_COLUMNS: tuple[str, ...] = ("Time", "Open", "High", "Low", "Close")

    def load(self, csv_path: str | Path) -> list[Bar]:
        frame = pd.read_csv(csv_path)
        missing = [c for c in self.REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        times = pd.to_datetime(frame["Time"], utc=True)
        volume_series = frame["Volume"] if "Volume" in frame.columns else 0.0

        bars: list[Bar] = []
        for idx in range(len(frame)):
            bars.append(
                Bar(
                    time=times.iloc[idx].to_pydatetime(),
                    open=float(frame["Open"].iloc[idx]),
                    high=float(frame["High"].iloc[idx]),
                    low=float(frame["Low"].iloc[idx]),
                    close=float(frame["Close"].iloc[idx]),
                    volume=float(volume_series.iloc[idx]) if hasattr(volume_series, "iloc") else 0.0,
                )
            )
        return bars
