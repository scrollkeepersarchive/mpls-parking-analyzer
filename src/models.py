from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    """A normalized event at or near Target Field."""

    name: str
    start_dt: datetime      # timezone-aware, America/Chicago
    venue: str
    source: str             # 'mlb', 'ticketmaster', 'ical'
    is_home_game: bool = False


@dataclass
class ScoredEvent:
    """An event paired with its parking impact score."""

    event: Event
    impact: str             # 'HIGH', 'MEDIUM', 'LOW'
    reason: str
