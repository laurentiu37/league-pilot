from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

from app.domain.team import Team
from app.domain.venue import Venue
from app.domain.game import Game
from app.domain.scheduler import Scheduler
from app.domain.results import ResultSimulator


@dataclass
class SupercupConfig:
    match_day: date
    search_days: int = 7
    neutral_venue_name: Optional[str] = None
    label: str = "SUPERCUPA ROMANIEI"


class SupercupEngine:
    def __init__(self, scheduler: Scheduler, sim: ResultSimulator, cfg: SupercupConfig):
        self.scheduler = scheduler
        self.sim = sim
        self.cfg = cfg

    def play(self, champion: Team, vice: Team, cup_winner: Team, venues_by_team: Dict[str, List[Venue]]) -> Game:
        opponent = vice if champion.id == cup_winner.id else cup_winner
        reason = "Cup winner = champion -> vs vice" if opponent.id == vice.id else "Champion vs Cup winner"

        if self.cfg.neutral_venue_name:
            venue = Venue(self.cfg.neutral_venue_name, home_team_id="NEUTRAL")
            self.scheduler.cal.venue_busy.setdefault(venue.id, [])
        else:
            venue = venues_by_team[champion.id][0]

        g = Game(stage="SUPERCUP", label=self.cfg.label, home=champion, away=opponent, venue=venue)
        g.notes.append(reason)

        start = self.cfg.match_day - timedelta(days=self.cfg.search_days)
        end = self.cfg.match_day + timedelta(days=self.cfg.search_days)

        ok = self.scheduler.schedule_game_in_window(g, (start, end), preferred_weekdays=None,
                                                    allow_alternate_venues=True, randomize=True)
        if ok:
            self.sim.simulate_game(g)
        else:
            g.notes.append("ERROR: could not schedule supercup in desired window")
        return g
