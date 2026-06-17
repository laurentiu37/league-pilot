from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta, time
from typing import List, Dict, Optional, Any
from app.domain.player import Player

from app.infrastructure.season_config import (
    SEASON_START, SEASON_END,
    CUP_QUALIFIERS_START, CUP_FINAL8_DAY1, CUP_Q1_START, CUP_Q1_END,
    PLAYOFF_START, SUPERCUP_DAY, CUP_Q2_START, CUP_Q2_END
)

from app.infrastructure.teams import load_teams_and_venues
from app.infrastructure.rosters import load_rosters_by_team_name
from app.infrastructure.previous_season import (
    resolve_previous_season_order,
    resolve_previous_cup_winner,
    previous_season_order_names
)
from app.infrastructure.team_strength import compute_strength_from_previous_season

from app.infrastructure.input_validation import (
    validate_teams_and_venues,
    validate_previous_season,
    validate_rosters
)

from app.events.event_log import EventLog
from app.events.dynamic_events import DynamicEvents, DynamicEventsConfig

from app.domain.constraints import Constraints
from app.domain.scheduler import Scheduler

from app.competitions.regular_season import RegularSeason, RegularSeasonConfig
from app.competitions.playoff import run_playoff_and_playout, PlayoffConfig
from app.competitions.cup import run_cupa_romaniei, CupConfig
from app.competitions.supercup import SupercupEngine, SupercupConfig

from app.domain.results import ResultSimulator, ResultSimulatorConfig
from app.domain.standings import Standings

from app.domain.game import Game
from app.domain.team import Team


@dataclass
class SimulateSeasonParams:
    seed: Optional[int] = None

    # dynamic events probabilities
    p_covid_per_round: float = 0.05
    p_venue_block_per_round: float = 0.03
    p_concert_per_round: float = 0.18
    p_injury_per_round: float = 0.06
    p_callup_per_round: float = 0.12
    p_covid_player_outbreak_per_round: float = 0.04

    # scheduling / TV
    time_slots: List[time] = None
    tv_featured_per_round: int = 1
    tv_allowed_times: Optional[List[time]] = None
    tv_requested_time: Optional[time] = None


@dataclass
class SimulateSeasonResult:
    teams: List[Team]
    rosters_by_team_id: Dict[str, List[Player]]
    all_games: List[Game]
    regular_games: List[Game]
    cup_games: List[Game]
    playoff_games: List[Game]
    regular_table: Any  # List[StandingsRow]
    final_order: List[Team]
    cup_winner: Team
    supercup_game: Game
    log_text: str
    seed: int


def _group_by_round_label(games: List[Game]) -> List[List[Game]]:
    rounds: Dict[str, List[Game]] = {}
    for g in games:
        rounds.setdefault(g.label, []).append(g)

    def key(lbl: str) -> int:
        try:
            return int(lbl.split()[-1])
        except ValueError:
            return 10**9

    return [rounds[k] for k in sorted(rounds.keys(), key=key)]


def simulate_season(params: SimulateSeasonParams) -> SimulateSeasonResult:
    # defaults
    if params.time_slots is None:
        params.time_slots = [time(17, 0), time(17, 15), time(17, 30), time(17, 45),
                             time(18, 0), time(18, 15), time(18, 30), time(18, 45),
                             time(19, 0), time(19, 15), time(19, 30), time(19, 45),
                             time(20, 0), time(20, 15), time(20, 30), time(20, 45), time(21, 0)]

    # ================= LOAD DATA =================
    teams, venues, venues_by_team = load_teams_and_venues()
    validate_teams_and_venues(teams, venues_by_team)
    validate_previous_season(previous_season_order_names(), teams)

    rosters_by_name = load_rosters_by_team_name()
    validate_rosters(rosters_by_name, teams)
    rosters_by_team_id = {t.id: rosters_by_name[t.name] for t in teams}

    prev_order = resolve_previous_season_order(teams)
    prev_cup_winner = resolve_previous_cup_winner(teams)
    strength = compute_strength_from_previous_season(prev_order)

    log = EventLog()

    # ================= CONSTRAINTS =================
    hard_blocks = [
        (CUP_FINAL8_DAY1, CUP_FINAL8_DAY1 + timedelta(days=4)),
        (CUP_Q1_START, CUP_Q1_END),
        (CUP_Q2_START, CUP_Q2_END),
    ]
    constraints = Constraints(hard_block_windows=hard_blocks)

    sched = Scheduler(
        teams=teams,
        venues=venues,
        constraints=constraints,
        match_duration_hours=2,
        time_slots=params.time_slots,
        season_end=SEASON_END,
        seed=params.seed,
        event_log=log
    )

    regular_reschedule_end = PLAYOFF_START - timedelta(days=1)

    # ================= DYNAMIC EVENTS =================
    dyn = DynamicEvents(
        sched,
        log,
        DynamicEventsConfig(
            p_covid_per_round=params.p_covid_per_round,
            p_venue_block_per_round=params.p_venue_block_per_round,
            p_concert_per_round=params.p_concert_per_round,
            p_injury_per_round=params.p_injury_per_round,
            p_callup_per_round=params.p_callup_per_round,
            p_covid_player_outbreak_per_round=params.p_covid_player_outbreak_per_round,
        ),
        seed=params.seed,
        rosters_by_team_id=rosters_by_team_id
    )

    # ================= SIMULATOR =================
    sim = ResultSimulator(
        ResultSimulatorConfig(
            strength_by_team=strength,
            rosters_by_team_id=rosters_by_team_id,
            unavailable_players=dyn.unavailable_players_for_team_on,
            seed=params.seed
        )
    )
    standings = Standings(teams)

    # ================= SUPERCUP =================
    sc = SupercupEngine(sched, sim, SupercupConfig(match_day=SUPERCUP_DAY, neutral_venue_name=None))
    champion = prev_order[0]
    vice = prev_order[1]
    supercup_game = sc.play(champion=champion, vice=vice, cup_winner=prev_cup_winner, venues_by_team=venues_by_team)

    # ================= REGULAR SEASON =================
    rs = RegularSeason(
        teams, venues_by_team, sched,
        RegularSeasonConfig(
            season_start=SEASON_START,
            tv_featured_per_round=params.tv_featured_per_round,
            prefer_weekend=True
        ),
        seed=params.seed
    )
    regular_games = rs.generate()
    rounds = _group_by_round_label([g for g in regular_games if g.stage == "REGULAR"])

    for round_games in rounds:
        cur_day = SEASON_START
        for g in round_games:
            if g.slot:
                cur_day = g.slot.date
                break

        allowed = params.tv_allowed_times or params.time_slots
        # try to force the TV start time
        for g in round_games:
            if g.tv_featured and g.slot:
                sched.try_change_start_time(g, allowed)

        dyn.maybe_trigger_round_events(
            regular_games, teams, venues, cur_day,
            reschedule_end=regular_reschedule_end
        )

        for g in round_games:
            sim.simulate_game(g)

    regular_table = standings.compute(regular_games, stage="REGULAR")

    # ================= CUPA =================
    cup_winner, cup_games, _phases = run_cupa_romaniei(
        scheduler=sched,
        venues_by_team=venues_by_team,
        sim=sim,
        cfg=CupConfig(qualifiers_start=CUP_QUALIFIERS_START, final8_day1=CUP_FINAL8_DAY1, seed=params.seed),
        prev_season_order=prev_order,
        prev_cup_winner=prev_cup_winner
    )

    # ================= PLAYOFF/PLAYOUT =================
    po_games, final_order = run_playoff_and_playout(
        scheduler=sched,
        venues_by_team=venues_by_team,
        sim=sim,
        cfg=PlayoffConfig(start_date=PLAYOFF_START),
        regular_table=regular_table
    )

    all_games = [supercup_game] + regular_games + cup_games + po_games

    return SimulateSeasonResult(
        teams=teams,
        rosters_by_team_id=rosters_by_team_id,
        all_games=all_games,
        regular_games=regular_games,
        cup_games=cup_games,
        playoff_games=po_games,
        regular_table=regular_table,
        final_order=final_order,
        cup_winner=cup_winner,
        supercup_game=supercup_game,
        log_text=log.dump(),
        seed=int(params.seed or 0)
    )
