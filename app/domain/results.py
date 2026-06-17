from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Set, List
from datetime import date
import random

from app.domain.game import Game
from app.domain.team import Team
from app.domain.player import Player


@dataclass
class ResultSimulatorConfig:
    # team_id -> coef
    strength_by_team: Dict[str, float]

    # Optional: rosters used for generating player boxscores
    rosters_by_team_id: Optional[Dict[str, List[Player]]] = None

    # Optional: callback used to apply per-game penalties (injury/call-up/covid etc.)
    # signature: (team_id, day: date) -> set(player_id)
    unavailable_players: Optional[Callable[[str, date], Set[str]]] = None

    # Penalty applied to TEAM strength for each missing player (tweak as you like)
    missing_player_penalty: float = 0.035

    # Boxscore generation
    enable_player_stats: bool = True
    rotation_size: int = 9  # players considered for boxscore

    base_points_mean: float = 78.0
    base_points_std: float = 10.0
    home_advantage: float = 3.0
    noise_std: float = 4.0
    seed: Optional[int] = None


class ResultSimulator:
    def __init__(self, cfg: ResultSimulatorConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)

    def _strength(self, team: Team) -> float:
        return float(self.cfg.strength_by_team.get(team.id, 1.0))

    def _apply_missing_penalty(self, team: Team, day_obj) -> float:
        s = self._strength(team)
        if not self.cfg.unavailable_players:
            return s
        missing = self.cfg.unavailable_players(team.id, day_obj) or set()
        k = len(missing)
        if k <= 0:
            return s
        return max(0.3, s * (1.0 - k * self.cfg.missing_player_penalty))

    def _pick_rotation(self, team: Team, day_obj) -> List[Player]:
        roster = (self.cfg.rosters_by_team_id or {}).get(team.id, [])
        if not roster:
            return []
        missing = set()
        if self.cfg.unavailable_players:
            missing = self.cfg.unavailable_players(team.id, day_obj) or set()
        available = [p for p in roster if p.id not in missing]
        if not available:
            return []
        n = min(self.cfg.rotation_size, len(available))
        return self.rng.sample(available, n)

    def _player_weight(self, p: Player) -> float:
        pos = (p.pos or "").upper()
        h = float(getattr(p, "height_cm", 190) or 190)
        base = 1.0
        if pos in ("PG", "SG"):
            base += 0.10
        elif pos in ("SF",):
            base += 0.05
        elif pos in ("PF", "C"):
            base += 0.08
        base += (h - 190.0) / 500.0
        base *= self.rng.uniform(0.90, 1.10)
        return max(0.2, base)

    @staticmethod
    def _distribute_int_total(total: int, weights: List[float]) -> List[int]:
        if total <= 0 or not weights:
            return [0] * len(weights)

        wsum = sum(weights)
        if wsum <= 0:
            base = total // len(weights)
            out = [base] * len(weights)
            out[0] += total - base * len(weights)
            return out

        raw = [total * (w / wsum) for w in weights]
        ints = [int(x) for x in raw]
        rem = total - sum(ints)

        frac_idx = sorted(range(len(weights)), key=lambda i: (raw[i] - ints[i]), reverse=True)
        for i in frac_idx[:rem]:
            ints[i] += 1
        return ints

    def _write_boxscore_for_team(self, g: Game, team: Team, opp: Team, team_points: int, day_obj) -> None:
        if not self.cfg.enable_player_stats:
            return
        rotation = self._pick_rotation(team, day_obj)
        if not rotation:
            return

        # Minutes: 200 total (40*5), starters play more
        minutes_total = 200
        min_weights = [1.25 if i < 5 else 0.85 for i in range(len(rotation))]
        mins = self._distribute_int_total(minutes_total, min_weights)

        # Points
        p_weights = [self._player_weight(p) for p in rotation]
        pts = self._distribute_int_total(team_points, p_weights)

        # Rebounds
        reb_total = round(max((28.0, min(55.0, self.rng.gauss(40, 6)))))
        reb_weights = []
        for p in rotation:
            pos = (p.pos or "").upper()
            h = float(getattr(p, "height_cm", 190) or 190)
            w = 1.0 + (h - 185.0) / 60.0
            if pos in ("PF", "C"):
                w *= 1.25
            elif pos in ("SF",):
                w *= 1.05
            else:
                w *= 0.85
            w *= self.rng.uniform(0.90, 1.10)
            reb_weights.append(max(0.2, w))
        reb = self._distribute_int_total(reb_total, reb_weights)

        # Assists
        ast_total = round(max(10.0, min(35.0, self.rng.gauss(22, 4))))
        ast_weights = []
        for p in rotation:
            pos = (p.pos or "").upper()
            w = 1.0
            if pos == "PG":
                w *= 1.55
            elif pos == "SG":
                w *= 1.20
            elif pos == "SF":
                w *= 1.00
            else:
                w *= 0.70
            w *= self.rng.uniform(0.90, 1.10)
            ast_weights.append(max(0.2, w))
        ast = self._distribute_int_total(ast_total, ast_weights)

        for i, p in enumerate(rotation):
            g.player_stats[p.id] = {
                "team_id": team.id,
                "team_name": team.name,
                "opp_id": opp.id,
                "opp_name": opp.name,
                "pts": int(pts[i]),
                "reb": int(reb[i]),
                "ast": int(ast[i]),
                "min": int(mins[i]),
            }

    def simulate_game(self, g: Game) -> None:
        if g.slot is None or g.played:
            return

        sh = self._apply_missing_penalty(g.home, g.slot.date)
        sa = self._apply_missing_penalty(g.away, g.slot.date)

        if g.stage == "REGULAR":
            noise_scale = 0.65
        elif g.stage == "PLAYOFF":
            noise_scale = 0.90
        else:
            noise_scale = 1.10

        base = self.rng.gauss(self.cfg.base_points_mean, self.cfg.base_points_std)

        strength_diff = sh - sa
        expected_margin = strength_diff * 26.0

        margin_noise = self.cfg.noise_std * noise_scale
        margin = expected_margin + self.rng.gauss(0.0, margin_noise)
        margin += self.cfg.home_advantage

        home = base + margin / 2.0
        away = base - margin / 2.0

        common = self.rng.gauss(0.0, self.cfg.noise_std * 0.25)
        home += common
        away += common

        home = int(max(home, 55))
        away = int(max(away, 55))

        if home == away:
            home += 1

        g.home_score = home
        g.away_score = away
        g.played = True

        # Player boxscores
        if self.cfg.enable_player_stats and self.cfg.rosters_by_team_id:
            g.player_stats = {}
            self._write_boxscore_for_team(g, g.home, g.away, home, g.slot.date)
            self._write_boxscore_for_team(g, g.away, g.home, away, g.slot.date)
