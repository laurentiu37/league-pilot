from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import time
import uuid

from .team import Team
from .venue import Venue
from .timeslot import TimeSlot


@dataclass
class Game:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    stage: str = ""
    label: str = ""          # e.g., "Etapa 1" or series label
    home: Team = None        # type: ignore
    away: Team = None        # type: ignore
    venue: Venue = None      # type: ignore

    slot: Optional[TimeSlot] = None
    original_slot: Optional[TimeSlot] = None

    # result
    played: bool = False
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    # Per-game player stats (filled by ResultSimulator if enabled)
    # player_id -> {"team_id": str, "team_name": str, "opp_id": str, "opp_name": str,
    #               "pts": int, "reb": int, "ast": int, "min": int}
    player_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # TV soft constraint: only start time can be requested
    tv_featured: bool = False
    tv_requested_time: Optional[time] = None
    tv_confirmed: bool = False

    notes: List[str] = field(default_factory=list)