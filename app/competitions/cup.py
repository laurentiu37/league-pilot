from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import random

from app.domain.team import Team
from app.domain.venue import Venue
from app.domain.game import Game
from app.domain.scheduler import Scheduler
from app.domain.results import ResultSimulator
from app.infrastructure.season_config import CUP_Q1_START, CUP_Q1_END, CUP_Q2_START, CUP_Q2_END


@dataclass
class CupConfig:
    qualifiers_start: date
    final8_day1: date
    neutral_venue_name: Optional[str] = None
    per_game_search_days: int = 10
    seed: Optional[int] = None


class CupEngine:
    def __init__(self, scheduler: Scheduler, venues_by_team: Dict[str, List[Venue]],
                 sim: ResultSimulator, cfg: CupConfig):
        self.scheduler = scheduler
        self.venues_by_team = venues_by_team
        self.sim = sim
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)

    def _pairs(self, teams: List[Team]) -> List[Tuple[Team, Team]]:
        t = teams[:]
        self.rng.shuffle(t)
        return [(t[i], t[i + 1]) for i in range(0, len(t), 2)]

    # GENERALIZAT: accepta end_day optional
    def _two_legged(
        self,
        label_prefix: str,
        a: Team,
        b: Team,
        start_day: date,
        end_day: Optional[date] = None
    ) -> Tuple[Team, Team, List[Game]]:

        games: List[Game] = []

        # -------- LEG 1 --------
        g1 = Game(
            stage="CUP_Q",
            label=f"{label_prefix} L1",
            home=a,
            away=b,
            venue=self.venues_by_team[a.id][0]
        )

        window_end = end_day if end_day else start_day + timedelta(days=self.cfg.per_game_search_days)

        # Daca avem interval strict, leg1 trebuie sa fie suficient de devreme ca sa mai incapa leg2 (+2 zile)
        if end_day is not None:
            latest_leg1 = end_day - timedelta(days=2)
            if latest_leg1 < start_day:
                latest_leg1 = start_day
            window_end = min(window_end, latest_leg1)

        ok1 = self.scheduler.schedule_game_in_window(
            g1,
            (start_day, window_end),
            preferred_weekdays=None,
            allow_alternate_venues=True,
            randomize=True,
            ignore_hard_blocks=True
        )

        if ok1:
            self.sim.simulate_game(g1)

        games.append(g1)

        # -------- LEG 2 --------
        leg2_day = g1.slot.date + timedelta(days=2) if g1.slot else start_day + timedelta(days=2)

        # PROTECTIE: daca intervalul e strict si leg2 nu mai incape, fallback direct + pastram tie-ul complet in export
        if end_day is not None and leg2_day > end_day:
            winner = self.rng.choice([a, b])
            loser = b if winner is a else a

            for g in games:
                g.played = False
                g.home_score = None
                g.away_score = None
                g.notes.append("ADMIN_DECISION")

            g2 = Game(
                stage="CUP_Q",
                label=f"{label_prefix} L2",
                home=b,
                away=a,
                venue=self.venues_by_team[b.id][0]
            )
            g2.played = False
            g2.home_score = None
            g2.away_score = None
            g2.notes.append("ADMIN_DECISION")
            games.append(g2)

            return winner, loser, games

        window_end_leg2 = end_day if end_day else leg2_day + timedelta(days=self.cfg.per_game_search_days)

        g2 = Game(
            stage="CUP_Q",
            label=f"{label_prefix} L2",
            home=b,
            away=a,
            venue=self.venues_by_team[b.id][0]
        )

        ok2 = self.scheduler.schedule_game_in_window(
            g2,
            (leg2_day, window_end_leg2),
            preferred_weekdays=None,
            allow_alternate_venues=True,
            randomize=True,
            ignore_hard_blocks=True
        )

        if ok2:
            self.sim.simulate_game(g2)

        games.append(g2)

        # -------- DECIDE WINNER --------
        if not (g1.played and g2.played):
            winner = self.rng.choice([a, b])
            loser = b if winner is a else a
            for g in games:
                g.played = False
                g.home_score = None
                g.away_score = None
                g.notes.append("ADMIN_DECISION")
            return winner, loser, games

        a_total = g1.home_score + g2.away_score
        b_total = g1.away_score + g2.home_score

        # egal -> meci in overtime
        while a_total == b_total:
            g2.home_score += self.rng.randint(1, 6)
            g2.away_score += self.rng.randint(0, 5)
            a_total = g1.home_score + g2.away_score
            b_total = g1.away_score + g2.home_score

        return (a, b, games) if a_total > b_total else (b, a, games)

    # ACCEPTA end_day
    def qualifiers_round(
        self,
        round_label: str,
        teams: List[Team],
        start_day: date,
        end_day: Optional[date] = None
    ) -> Tuple[List[Team], List[Game]]:

        winners: List[Team] = []
        all_games: List[Game] = []

        for i, (a, b) in enumerate(self._pairs(teams), start=1):
            w, l, gs = self._two_legged(
                f"{round_label} TIE{i}",
                a,
                b,
                start_day,
                end_day
            )
            winners.append(w)
            all_games += gs

        return winners, all_games

    def final8(self, qualified4: List[Team], direct4: List[Team]) -> Tuple[Team, List[Game]]:

        if len(qualified4) != 4 or len(direct4) != 4:
            raise ValueError("Final8 needs 4+4 teams")

        teams8 = qualified4 + direct4
        self.rng.shuffle(teams8)

        host_team = self.rng.choice(teams8)

        host_venues = self.venues_by_team.get(host_team.id, [])
        if not host_venues:
            raise RuntimeError(f"No venues for host team {host_team.name}")

        host_venue = self.rng.choice(host_venues)

        day1 = self.cfg.final8_day1
        day2 = day1 + timedelta(days=1)
        day3 = day1 + timedelta(days=2)
        day5 = day1 + timedelta(days=4)  # day4 pause

        games: List[Game] = []
        qf_winners: List[Team] = []

        qf_pairs = [
            (teams8[0], teams8[1]),
            (teams8[2], teams8[3]),
            (teams8[4], teams8[5]),
            (teams8[6], teams8[7]),
        ]

        # QF1+QF2 day1, QF3+QF4 day2
        for idx, (a, b) in enumerate(qf_pairs, start=1):
            d = day1 if idx in (1, 2) else day2
            g = Game(stage="CUP_FINAL8", label=f"CUP QF{idx}", home=a, away=b, venue=host_venue)

            ok = self.scheduler.schedule_game_in_window(
                g,
                (d, d + timedelta(days=1)),
                preferred_weekdays=None,
                allow_alternate_venues=False,
                randomize=False,
                ignore_hard_blocks=True
            )

            if ok:
                self.sim.simulate_game(g)
                qf_winners.append(a if g.home_score > g.away_score else b)
            else:
                g.notes.append("ADMIN_DECISION")
                g.played = False
                g.home_score = None
                g.away_score = None
                qf_winners.append(self.rng.choice([a, b]))

            games.append(g)

        sf_pairs = [(qf_winners[0], qf_winners[1]), (qf_winners[2], qf_winners[3])]
        sf_winners: List[Team] = []

        for idx, (a, b) in enumerate(sf_pairs, start=1):
            g = Game(stage="CUP_FINAL8", label=f"CUP SF{idx}", home=a, away=b, venue=host_venue)

            ok = self.scheduler.schedule_game_in_window(
                g,
                (day3, day3 + timedelta(days=1)),
                preferred_weekdays=None,
                allow_alternate_venues=False,
                randomize=False,
                ignore_hard_blocks=True
            )

            if ok:
                self.sim.simulate_game(g)
                sf_winners.append(a if g.home_score > g.away_score else b)
            else:
                g.notes.append("ADMIN_DECISION")
                g.played = False
                g.home_score = None
                g.away_score = None
                sf_winners.append(self.rng.choice([a, b]))

            games.append(g)

        a, b = sf_winners
        g_final = Game(stage="CUP_FINAL8", label="CUP FINAL", home=a, away=b, venue=host_venue)

        ok = self.scheduler.schedule_game_in_window(
            g_final,
            (day5, day5 + timedelta(days=1)),
            preferred_weekdays=None,
            allow_alternate_venues=False,
            randomize=False,
            ignore_hard_blocks=True
        )

        if ok:
            self.sim.simulate_game(g_final)
            winner = a if g_final.home_score > g_final.away_score else b
        else:
            g_final.notes.append("ADMIN_DECISION")
            g_final.played = False
            g_final.home_score = None
            g_final.away_score = None
            winner = self.rng.choice([a, b])

        games.append(g_final)

        return winner, games


def run_cupa_romaniei(
    scheduler: Scheduler,
    venues_by_team: Dict[str, List[Venue]],
    sim: ResultSimulator,
    cfg: CupConfig,
    prev_season_order: List[Team],
    prev_cup_winner: Team,
) -> Tuple[Team, List[Game], dict]:

    engine = CupEngine(scheduler, venues_by_team, sim, cfg)

    direct4 = prev_season_order[:4]
    tur1 = prev_season_order[8:16]     # 9-16
    add_tur2 = prev_season_order[4:8]  # 5-8

    # Tur 1 STRICT 20–27 septembrie
    winners_t1, g1 = engine.qualifiers_round(
        "CUP 1/16",
        tur1,
        CUP_Q1_START,
        CUP_Q1_END
    )

    # Tur 2 STRICT 17–23 decembrie
    winners_t2, g2 = engine.qualifiers_round(
        "CUP 1/8",
        winners_t1 + add_tur2,
        CUP_Q2_START,
        CUP_Q2_END
    )

    cup_winner, g3 = engine.final8(winners_t2, direct4)

    phases = {
        "direct_qualified_top4": [t.name for t in direct4],
        "qual_round1_9_16": [t.name for t in tur1],
        "qual_round1_winners": [t.name for t in winners_t1],
        "qual_round2_add_5_8": [t.name for t in add_tur2],
        "qual_round2_winners": [t.name for t in winners_t2],
        "cup_winner": cup_winner.name,
        "previous_cup_winner": prev_cup_winner.name,
    }

    return cup_winner, (g1 + g2 + g3), phases
