from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import random

from app.domain.team import Team
from app.domain.venue import Venue
from app.domain.game import Game
from app.domain.scheduler import Scheduler


@dataclass
class RegularSeasonConfig:
    season_start: date
    tv_featured_per_round: int = 1
    prefer_weekend: bool = True
    round_spacing_days: int = 7  # 1 etapa pe saptamana (default)


class RegularSeason:
    def __init__(
        self,
        teams: List[Team],
        venues_by_team: Dict[str, List[Venue]],
        scheduler: Scheduler,
        cfg: RegularSeasonConfig,
        seed: Optional[int] = None
    ):
        if len(teams) % 2 != 0:
            raise ValueError("Need even number of teams")
        self.teams = teams
        self.venues_by_team = venues_by_team
        self.scheduler = scheduler
        self.cfg = cfg
        self.rng = random.Random(seed)

    @staticmethod
    def _round_robin_pairs(teams: List[Team]) -> List[List[Tuple[Team, Team]]]:
        # Circle method, even teams
        n = len(teams)
        arr = teams[:]
        rounds = []
        for r in range(n - 1):
            pairs = []
            for i in range(n // 2):
                a = arr[i]
                b = arr[n - 1 - i]
                pairs.append((a, b))
            # rotate (keep first fixed)
            arr = [arr[0]] + [arr[-1]] + arr[1:-1]
            rounds.append(pairs)
        return rounds

    def generate(self) -> List[Game]:
        # Initial ordering is alphabetical by team name (already sorted in data loader)
        first_leg = self._round_robin_pairs(self.teams)
        second_leg = [[(b, a) for (a, b) in rnd] for rnd in first_leg]  # swap home/away

        all_rounds = first_leg + second_leg
        games: List[Game] = []

        for idx, rnd in enumerate(all_rounds, start=1):
            label = f"Etapa {idx}"
            round_start = self.cfg.season_start + timedelta(days=(idx - 1) * self.cfg.round_spacing_days)
            while self.scheduler.constraints.is_hard_blocked(round_start):
                round_start += timedelta(days=7)

            # select TV featured games (soft)
            tv_indices = set(self.rng.sample(range(len(rnd)), k=min(self.cfg.tv_featured_per_round, len(rnd))))

            # schedule each game in this round within that week
            # preferred weekdays Fri/Sat/Sun if prefer_weekend
            preferred = [4, 5, 6] if self.cfg.prefer_weekend else None

            for j, (home, away) in enumerate(rnd):
                venue = self.venues_by_team[home.id][0]
                g = Game(stage="REGULAR", label=label, home=home, away=away, venue=venue)
                g.tv_featured = (j in tv_indices)
                ok = self.scheduler.schedule_game_in_window(
                    g,
                    (round_start, round_start + timedelta(days=6)),
                    preferred_weekdays=preferred,
                    allow_alternate_venues=True,
                    randomize=True
                )
                if not ok:
                    g.notes.append("WARNING: Could not schedule in preferred window; remains unscheduled.")
                games.append(g)

        return games
