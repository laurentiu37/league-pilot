from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

from app.domain.team import Team
from app.domain.venue import Venue
from app.domain.game import Game
from app.domain.scheduler import Scheduler
from app.domain.results import ResultSimulator
from app.domain.standings import StandingsRow


@dataclass
class PlayoffConfig:
    start_date: date
    # cat de mult are voie sa "impinga" o serie daca nu gaseste slot in ferestrele initiale
    # (te ajuta exact in cazurile random cand iti da ERROR: Could not schedule series game)
    max_series_search_days: int = 180


class SeriesFormat:
    @staticmethod
    def pattern(best_of: int) -> List[str]:
        if best_of == 5:
            return ["H", "H", "A", "A", "H"]
        if best_of == 7:
            return ["H", "H", "A", "A", "H", "A", "H"]
        raise ValueError("best_of must be 5 or 7")


class PlayoffEngine:
    def __init__(self, scheduler: Scheduler, venues_by_team: Dict[str, List[Venue]],
                 sim: ResultSimulator, cfg: PlayoffConfig):
        self.scheduler = scheduler
        self.venues_by_team = venues_by_team
        self.sim = sim
        self.cfg = cfg

    @staticmethod
    def _rest_days(last_loc: Optional[str], new_loc: str) -> int:
        if last_loc is None:
            return 0
        return 1 if last_loc == new_loc else 2

    def play_series(
        self,
        stage: str,
        label_prefix: str,
        higher_seed: Team,
        lower_seed: Team,
        best_of: int,
        start_date: date
    ) -> Tuple[Team, Team, List[Game]]:

        wins_needed = 3 if best_of == 5 else 4
        pat = SeriesFormat.pattern(best_of)

        w_hi = 0
        w_lo = 0
        last_loc: Optional[str] = None
        cursor = start_date
        games: List[Game] = []

        # limita globala pana unde avem voie sa impingem seria (si sezon_end daca exista)
        max_end = start_date + timedelta(days=self.cfg.max_series_search_days)
        if self.scheduler.season_end is not None:
            max_end = min(max_end, self.scheduler.season_end)

        for i, loc in enumerate(pat, start=1):
            if w_hi >= wins_needed or w_lo >= wins_needed:
                break

            cursor = cursor + timedelta(days=self._rest_days(last_loc, loc))
            last_loc = loc

            if loc == "H":
                home, away = higher_seed, lower_seed
            else:
                home, away = lower_seed, higher_seed

            venue = self.venues_by_team[home.id][0]
            g = Game(stage=stage, label=f"{label_prefix} G{i}", home=home, away=away, venue=venue)

            # --- NEW: retry "sliding window" ---
            # In loc sa incercam doar (cursor..cursor+7) o singura data,
            # incercam sa mutam cursorul zi cu zi pana gasim slot.
            ok = False
            search_cursor = cursor

            while search_cursor <= max_end:
                window_end = min(search_cursor + timedelta(days=7), max_end)

                ok = self.scheduler.schedule_game_in_window(
                    g,
                    (search_cursor, window_end),
                    preferred_weekdays=None,
                    allow_alternate_venues=True,
                    randomize=False
                )

                if ok:
                    break

                search_cursor = search_cursor + timedelta(days=1)

            if not ok:
                g.notes.append("ERROR: Could not schedule series game.")
                games.append(g)
                break

            self.sim.simulate_game(g)
            games.append(g)

            # update wins
            if g.home_score > g.away_score:
                if g.home.id == higher_seed.id:
                    w_hi += 1
                else:
                    w_lo += 1
            else:
                if g.away.id == higher_seed.id:
                    w_hi += 1
                else:
                    w_lo += 1

            cursor = g.slot.date

        return (higher_seed, lower_seed, games) if w_hi > w_lo else (lower_seed, higher_seed, games)

    @staticmethod
    def bracket_pairs(seeded: List[Team]) -> List[Tuple[Team, Team]]:
        return [(seeded[0], seeded[7]), (seeded[1], seeded[6]), (seeded[2], seeded[5]), (seeded[3], seeded[4])]

    @staticmethod
    def _next_round_start(games: List[Game], fallback: date, rest_days: int = 7) -> date:
        played_dates = [g.slot.date for g in games if g.slot is not None]
        if not played_dates:
            return fallback + timedelta(days=rest_days)

        last_played = max(played_dates)

        # calculam data teoretica a meciului 5, chiar daca seria s-a incheiat mai devreme
        remaining_to_game_5 = max(0, 5 - len(played_dates))
        theoretical_game_5_date = last_played + timedelta(days=remaining_to_game_5 * 2)

        return theoretical_game_5_date + timedelta(days=rest_days)

    def run_playoff_top8(self, top8: List[Team]) -> Tuple[List[Game], List[Team]]:
        all_games: List[Game] = []
        start = self.cfg.start_date

        # QF Bo5 - toate sferturile pornesc in paralel
        qf_games: List[Game] = []
        qf_w, qf_l = [], []

        for i, (hi, lo) in enumerate(self.bracket_pairs(top8), start=1):
            w, l, gs = self.play_series("PLAYOFF", f"PO QF{i}", hi, lo, 5, start)
            qf_games += gs
            qf_w.append(w)
            qf_l.append(l)

        all_games += qf_games

        # Semifinalele pornesc după ce se termina sferturile
        sf_start = self._next_round_start(qf_games, start)

        sf_games: List[Game] = []
        sf_pairs = [(qf_w[0], qf_w[3]), (qf_w[1], qf_w[2])]
        sf_w, sf_l = [], []

        for i, (a, b) in enumerate(sf_pairs, start=1):
            hi = a if top8.index(a) < top8.index(b) else b
            lo = b if hi is a else a
            w, l, gs = self.play_series("PLAYOFF", f"PO SF{i}", hi, lo, 5, sf_start)
            sf_games += gs
            sf_w.append(w)
            sf_l.append(l)

        all_games += sf_games

        # Finala si locul 3 pornesc dupa semifinale
        medal_start = self._next_round_start(sf_games, sf_start)

        medal_games: List[Game] = []

        hi = sf_l[0] if top8.index(sf_l[0]) < top8.index(sf_l[1]) else sf_l[1]
        lo = sf_l[1] if hi is sf_l[0] else sf_l[0]
        w3, l4, gs = self.play_series("PLAYOFF", "PO 3RD", hi, lo, 5, medal_start)
        medal_games += gs

        hi = sf_w[0] if top8.index(sf_w[0]) < top8.index(sf_w[1]) else sf_w[1]
        lo = sf_w[1] if hi is sf_w[0] else sf_w[0]
        champ, runner, gs = self.play_series("PLAYOFF", "PO FINAL", hi, lo, 7, medal_start)
        medal_games += gs

        all_games += medal_games

        # Placement 5-8 porneste dupa sferturi, in paralel cu semifinalele
        placement_5_8_start = sf_start

        pA = (qf_l[0], qf_l[3])
        pB = (qf_l[1], qf_l[2])

        def better(a, b):
            return (a, b) if top8.index(a) < top8.index(b) else (b, a)

        placement_sf_games: List[Game] = []

        hi, lo = better(*pA)
        wA, lA, gs = self.play_series("PLAYOFF", "PO 5-8 SF-A", hi, lo, 5, placement_5_8_start)
        placement_sf_games += gs

        hi, lo = better(*pB)
        wB, lB, gs = self.play_series("PLAYOFF", "PO 5-8 SF-B", hi, lo, 5, placement_5_8_start)
        placement_sf_games += gs

        all_games += placement_sf_games

        # Locurile 5 si 7 pornesc dupa seriile 5-8, nu dupa toate meciurile
        placement_final_start = self._next_round_start(placement_sf_games, placement_5_8_start)

        placement_final_games: List[Game] = []

        hi, lo = better(wA, wB)
        w5, l6, gs = self.play_series("PLAYOFF", "PO 5TH", hi, lo, 5, placement_final_start)
        placement_final_games += gs

        hi, lo = better(lA, lB)
        w7, l8, gs = self.play_series("PLAYOFF", "PO 7TH", hi, lo, 5, placement_final_start)
        placement_final_games += gs

        all_games += placement_final_games

        order = [champ, runner, w3, l4, w5, l6, w7, l8]
        return all_games, order

    def run_playout_bottom8(self, bottom8: List[Team]) -> Tuple[List[Game], List[Team]]:
        all_games: List[Game] = []
        start = self.cfg.start_date

        # QF Bo5 - toate sferturile pornesc in paralel
        qf_games: List[Game] = []
        qf_w, qf_l = [], []

        for i, (hi, lo) in enumerate(self.bracket_pairs(bottom8), start=1):
            w, l, gs = self.play_series("PLAYOUT", f"PL QF{i}", hi, lo, 5, start)
            qf_games += gs
            qf_w.append(w)
            qf_l.append(l)

        all_games += qf_games

        # Semifinalele pornesc dupa sferturi
        sf_start = self._next_round_start(qf_games, start)

        sf_games: List[Game] = []
        sf_pairs = [(qf_w[0], qf_w[3]), (qf_w[1], qf_w[2])]
        sf_w, sf_l = [], []

        for i, (a, b) in enumerate(sf_pairs, start=1):
            hi = a if bottom8.index(a) < bottom8.index(b) else b
            lo = b if hi is a else a
            w, l, gs = self.play_series("PLAYOUT", f"PL SF{i}", hi, lo, 5, sf_start)
            sf_games += gs
            sf_w.append(w)
            sf_l.append(l)

        all_games += sf_games

        # Locurile 9 si 11 pornesc dupa semifinalele principale
        placement_9_12_start = self._next_round_start(sf_games, sf_start)

        placement_9_12_games: List[Game] = []

        hi = sf_w[0] if bottom8.index(sf_w[0]) < bottom8.index(sf_w[1]) else sf_w[1]
        lo = sf_w[1] if hi is sf_w[0] else sf_w[0]
        w9, l10, gs = self.play_series("PLAYOUT", "PL 9TH", hi, lo, 5, placement_9_12_start)
        placement_9_12_games += gs

        hi = sf_l[0] if bottom8.index(sf_l[0]) < bottom8.index(sf_l[1]) else sf_l[1]
        lo = sf_l[1] if hi is sf_l[0] else sf_l[0]
        w11, l12, gs = self.play_series("PLAYOUT", "PL 11TH", hi, lo, 5, placement_9_12_start)
        placement_9_12_games += gs

        all_games += placement_9_12_games

        # Placement 13-16 porneste dupa sferturi, nu dupa toate meciurile
        placement_13_16_start = sf_start

        pA = (qf_l[0], qf_l[3])
        pB = (qf_l[1], qf_l[2])

        def better(a, b):
            return (a, b) if bottom8.index(a) < bottom8.index(b) else (b, a)

        placement_13_16_sf_games: List[Game] = []

        hi, lo = better(*pA)
        wA, lA, gs = self.play_series("PLAYOUT", "PL 13-16 SF-A", hi, lo, 5, placement_13_16_start)
        placement_13_16_sf_games += gs

        hi, lo = better(*pB)
        wB, lB, gs = self.play_series("PLAYOUT", "PL 13-16 SF-B", hi, lo, 5, placement_13_16_start)
        placement_13_16_sf_games += gs

        all_games += placement_13_16_sf_games

        # Locurile 13 si 15 pornesc dupa seriile 13-16
        placement_13_16_final_start = self._next_round_start(
            placement_13_16_sf_games,
            placement_13_16_start
        )

        placement_13_16_final_games: List[Game] = []

        hi, lo = better(wA, wB)
        w13, l14, gs = self.play_series("PLAYOUT", "PL 13TH", hi, lo, 5, placement_13_16_final_start)
        placement_13_16_final_games += gs

        hi, lo = better(lA, lB)
        w15, l16, gs = self.play_series("PLAYOUT", "PL 15TH", hi, lo, 5, placement_13_16_final_start)
        placement_13_16_final_games += gs

        all_games += placement_13_16_final_games

        order = [w9, l10, w11, l12, w13, l14, w15, l16]
        return all_games, order


def run_playoff_and_playout(
    scheduler: Scheduler,
    venues_by_team: Dict[str, List[Venue]],
    sim: ResultSimulator,
    cfg: PlayoffConfig,
    regular_table: List[StandingsRow]
) -> Tuple[List[Game], List[Team]]:

    engine = PlayoffEngine(scheduler, venues_by_team, sim, cfg)
    ordered = [r.team for r in regular_table]
    top8 = ordered[:8]
    bottom8 = ordered[8:]

    po_games, top_order = engine.run_playoff_top8(top8)
    pl_games, bottom_order = engine.run_playout_bottom8(bottom8)

    return po_games + pl_games, top_order + bottom_order
