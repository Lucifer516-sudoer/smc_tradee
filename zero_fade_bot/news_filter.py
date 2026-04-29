from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewsEvent:
    at_utc: datetime
    impact: str
    title: str


class EconomicCalendarFilter:
    """
    Stub calendar filter with injectable implementation.

    Replace `get_upcoming_events` with your preferred provider integration.
    """

    def get_upcoming_events(self, symbol: str, now_utc: datetime) -> list[NewsEvent]:
        _ = symbol, now_utc
        return []

    def is_news_blackout(self, symbol: str, now_utc: datetime) -> bool:
        events: list[NewsEvent] = self.get_upcoming_events(
            symbol=symbol, now_utc=now_utc
        )
        window: timedelta = timedelta(minutes=30)
        for event in events:
            if event.impact.lower() != "high":
                continue
            if abs((event.at_utc - now_utc).total_seconds()) <= window.total_seconds():
                logger.info(
                    f"{symbol}: red-folder blackout active due to '{event.title}'."
                )
                return True
        return False


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
