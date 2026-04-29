from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .models import Bar


class CsvDataLoader:
    """Loads ForexSB-style CSV into normalized bars."""

    REQUIRED_COLUMNS: tuple[str, ...] = ("Time", "Open", "High", "Low", "Close")

    def load(
        self,
        csv_path: str | Path,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Bar]:
        # Try tab delimiter first (ForexSB format), fall back to comma
        try:
            frame = pd.read_csv(csv_path, sep="\t")
            if not all(col in frame.columns for col in self.REQUIRED_COLUMNS):
                frame = pd.read_csv(csv_path, sep=",")
        except Exception:
            frame = pd.read_csv(csv_path)

        missing = [c for c in self.REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        # Parse datetime - handle multiple formats
        times = pd.to_datetime(frame["Time"], format="mixed", utc=True)

        # Filter by date range if provided
        if start_date is not None:
            mask = times >= pd.Timestamp(start_date)
            frame = frame[mask]
            times = times[mask]

        if end_date is not None:
            mask = times <= pd.Timestamp(end_date)
            frame = frame[mask]
            times = times[mask]

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
                    volume=float(volume_series.iloc[idx])
                    if hasattr(volume_series, "iloc")
                    else 0.0,
                )
            )
        return bars
