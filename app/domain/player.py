from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    """Simple player model used across roster loading, simulation, API and DB layers."""

    id: str          # stable identifier (e.g. "oradea_01")
    name: str        # display name
    pos: str         # PG/SG/SF/PF/C or combined like "PF/C"
    height_cm: int   # height in centimeters
