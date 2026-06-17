from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List


class SimulateRequest(BaseModel):
    seed: Optional[int] = Field(default=None, examples=[None])

    # probabilitati evenimente dinamice
    p_covid_per_round: float = Field(default=0.05, ge=0, le=1)
    p_venue_block_per_round: float = Field(default=0.03, ge=0, le=1)
    p_concert_per_round: float = Field(default=0.18, ge=0, le=1)

    p_injury_per_round: float = Field(default=0.06, ge=0, le=1)
    p_callup_per_round: float = Field(default=0.12, ge=0, le=1)
    p_covid_player_outbreak_per_round: float = Field(default=0.04, ge=0, le=1)

    tv_featured_per_round: int = Field(default=1, ge=0, le=8)

    # format time slots "HH:MM"
    time_slots: List[str] = Field(
        default_factory=lambda: ["17:00", "17:15", "17:30", "17:45",
                                 "18:00", "18:15", "18:30", "18:45",
                                 "19:00", "19:15", "19:30", "19:45",
                                 "20:00", "20:15", "20:30", "20:45", "21:00"],
        examples=[["17:00", "17:15", "17:30", "17:45",
                   "18:00", "18:15", "18:30", "18:45",
                   "19:00", "19:15", "19:30", "19:45",
                   "20:00", "20:15", "20:30", "20:45", "21:00"]],
    )
    tv_requested_time: str | None = Field(
        default=None,
        examples=[None, "17:00", "17:15", "17:30", "17:45",
                  "18:00", "18:15", "18:30", "18:45",
                  "19:00", "19:15", "19:30", "19:45",
                  "20:00", "20:15", "20:30", "20:45", "21:00"],
    )
    tv_allowed_times: List[str] | None = Field(
        default=None,
        examples=[None, "17:00", "17:15", "17:30", "17:45",
                  "18:00", "18:15", "18:30", "18:45",
                  "19:00", "19:15", "19:30", "19:45",
                  "20:00", "20:15", "20:30", "20:45", "21:00"],
    )


class SimulateResponse(BaseModel):
    run_id: int
    message: str
    seed: int


class RunSummary(BaseModel):
    run_id: int
    cup_winner: str
    champion: str
    vice: str
    supercup_winner: str | None
    games_count: int
