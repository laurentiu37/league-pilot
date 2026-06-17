from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import defaultdict

from app.domain.game import Game
from app.domain.team import Team


@dataclass
class StandingsRow:
    team: Team
    played: int = 0
    wins: int = 0
    losses: int = 0
    points: int = 0   # 2 per victorie / 1 per infrangere
    pf: int = 0
    pa: int = 0

    @property
    def diff(self) -> int:
        return self.pf - self.pa


class Standings:
    def __init__(self, teams: List[Team]):
        self.teams = teams
        self.rows: Dict[str, StandingsRow] = {t.id: StandingsRow(team=t) for t in teams}
        self.h2h_points = defaultdict(lambda: defaultdict(int))  # key(sorted pair)-> team_id->points

    def _add_h2h(self, a: str, b: str, winner: str) -> None:
        key = tuple(sorted([a, b]))
        loser = b if winner == a else a
        self.h2h_points[key][winner] += 2
        self.h2h_points[key][loser] += 1

    def apply_game(self, g: Game) -> None:
        if not g.played or g.home_score is None or g.away_score is None:
            return
        rh = self.rows[g.home.id]
        ra = self.rows[g.away.id]
        rh.played += 1
        ra.played += 1
        rh.pf += g.home_score
        rh.pa += g.away_score
        ra.pf += g.away_score
        ra.pa += g.home_score

        if g.home_score > g.away_score:
            rh.wins += 1
            ra.losses += 1
            rh.points += 2
            ra.points += 1
            self._add_h2h(g.home.id, g.away.id, winner=g.home.id)
        else:
            ra.wins += 1
            rh.losses += 1
            ra.points += 2
            rh.points += 1
            self._add_h2h(g.home.id, g.away.id, winner=g.away.id)

    def compute(self, games: List[Game], stage: Optional[str] = "REGULAR") -> List[StandingsRow]:
        self.rows = {t.id: StandingsRow(team=t) for t in self.teams}
        self.h2h_points.clear()
        for g in games:
            if stage is None or g.stage == stage:
                self.apply_game(g)
        return self.sorted_rows()

    def _h2h_points_in_group(self, team_id: str, group_ids: List[str]) -> int:
        total = 0
        for other in group_ids:
            if other == team_id:
                continue
            key = tuple(sorted([team_id, other]))
            total += self.h2h_points.get(key, {}).get(team_id, 0)
        return total

    def sorted_rows(self) -> List[StandingsRow]:
        rows = list(self.rows.values())
        rows.sort(key=lambda r: r.points, reverse=True)

        final: List[StandingsRow] = []
        i = 0
        while i < len(rows):
            j = i
            while j < len(rows) and rows[j].points == rows[i].points:
                j += 1
            group = rows[i:j]
            if len(group) == 1:
                final.append(group[0])
            else:
                group_ids = [r.team.id for r in group]
                group.sort(key=lambda r: self._h2h_points_in_group(r.team.id, group_ids), reverse=True)

                k = 0
                while k < len(group):
                    m = k
                    h2hk = self._h2h_points_in_group(group[k].team.id, group_ids)
                    while m < len(group) and self._h2h_points_in_group(group[m].team.id, group_ids) == h2hk:
                        m += 1
                    sub = group[k:m]
                    sub.sort(key=lambda r: r.diff, reverse=True)
                    final.extend(sub)
                    k = m
            i = j

        return final
