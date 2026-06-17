from __future__ import annotations
from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class TimeSlot:
    date: date
    start: time
    duration_hours: int = 2
