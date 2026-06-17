from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple, Dict, Set
import random

from app.domain.game import Game
from app.domain.team import Team
from app.domain.venue import Venue
from app.domain.player import Player
from app.domain.scheduler import Scheduler
from .event_log import EventLog
from app.infrastructure.season_config import NATIONAL_TEAM_BREAKS

DateWindow = Tuple[date, date]


@dataclass
class DynamicEventsConfig:
    # Team / venue level events (existing)
    p_covid_per_round: float = 0.05
    p_venue_block_per_round: float = 0.03
    p_concert_per_round: float = 0.18

    # Player-level events (new)
    p_injury_per_round: float = 0.06
    p_callup_per_round: float = 0.12
    p_covid_player_outbreak_per_round: float = 0.04

    # window lengths
    covid_days: int = 10
    venue_block_days: int = 2

    injury_days: int = 14
    callup_days: int = 10
    covid_players_min: int = 2
    covid_players_max: int = 5


class DynamicEvents:
    def __init__(
        self,
        scheduler: Scheduler,
        log: EventLog,
        cfg: Optional[DynamicEventsConfig] = None,
        seed: Optional[int] = None,
        *,
        rosters_by_team_id: Optional[Dict[str, List[Player]]] = None,
    ):
        self.scheduler = scheduler
        self.log = log
        self.cfg = cfg or DynamicEventsConfig()
        self.rng = random.Random(seed)

        self.rosters_by_team_id: Dict[str, List[Player]] = rosters_by_team_id or {}
        # player_id -> list of (start, end, reason)
        self.player_absences: Dict[str, List[Tuple[date, date, str]]] = {}

    # ===== Player availability API (used by ResultSimulator) =====

    def mark_player_absent(self, player_id: str, window: DateWindow, reason: str) -> None:
        a, b = window
        self.player_absences.setdefault(player_id, []).append((a, b, reason))

    def unavailable_players_for_team_on(self, team_id: str, day: date) -> Set[str]:
        roster = self.rosters_by_team_id.get(team_id, [])
        out: Set[str] = set()
        for p in roster:
            for a, b, _reason in self.player_absences.get(p.id, []):
                if a <= day <= b:
                    out.add(p.id)
                    break
        return out

    # ===== Round triggers =====

    def maybe_trigger_round_events(
        self,
        all_games: List[Game],
        teams: List[Team],
        venues: List[Venue],
        current_day: date,
        reschedule_end: Optional[date] = None,
    ) -> None:
        # ---------------- Team / venue events ----------------

        # COVID (team unavailable)
        if self.rng.random() < self.cfg.p_covid_per_round:
            team = self.rng.choice(teams)
            window = (current_day, current_day + timedelta(days=self.cfg.covid_days))
            self.team_unavailable(team, window, all_games, reschedule_end=reschedule_end)

        # Venue blocked
        if self.rng.random() < self.cfg.p_venue_block_per_round:
            venue = self.rng.choice(venues)
            window = (current_day, current_day + timedelta(days=self.cfg.venue_block_days))
            self.venue_blocked(venue, window, all_games, reschedule_end=reschedule_end)

        # Concert (venue occupied) -> try move to secondary venue
        if self.rng.random() < self.cfg.p_concert_per_round:
            self.maybe_concert_event(all_games, current_day, reschedule_end=reschedule_end)

        # ---------------- Player-level events ----------------
        if not self.rosters_by_team_id:
            return

        # Injury (any time)
        if self.rng.random() < self.cfg.p_injury_per_round:
            team = self.rng.choice(teams)
            window = (current_day, current_day + timedelta(days=self.cfg.injury_days))
            self.player_injury(team, window, all_games)

        # COVID outbreak on players (any time)
        if self.rng.random() < self.cfg.p_covid_player_outbreak_per_round:
            team = self.rng.choice(teams)
            window = (current_day, current_day + timedelta(days=self.cfg.covid_days))
            self.covid_outbreak_players(team, window, all_games)

        # Call-ups only during national-team breaks
        for a, b in NATIONAL_TEAM_BREAKS:
            if a <= current_day <= b:
                if self.rng.random() < self.cfg.p_callup_per_round:
                    team = self.rng.choice(teams)
                    window = (a, b)
                    self.player_callup(team, window, all_games)
                break

    # ===== Player-level events =====

    def player_injury(self, team: Team, window: DateWindow, games: List[Game]) -> None:
        roster = self.rosters_by_team_id.get(team.id, [])
        if not roster:
            return
        p = self.rng.choice(roster)
        self.mark_player_absent(p.id, window, "INJURY")
        self.log.add("PLAYER_INJURY", f"{team.name}: {p.name} OUT {window[0]}..{window[1]}")
        self._tag_games_with_player_absence(team, p, window, games, "INJURY")

    def player_callup(self, team: Team, window: DateWindow, games: List[Game]) -> None:
        roster = self.rosters_by_team_id.get(team.id, [])
        if not roster:
            return
        k = 1 if len(roster) < 10 else 2
        picked = self.rng.sample(roster, k=min(k, len(roster)))
        for p in picked:
            self.mark_player_absent(p.id, window, "CALLED_UP")
            self.log.add("PLAYER_CALLUP", f"{team.name}: {p.name} CALLED UP {window[0]}..{window[1]}")
            self._tag_games_with_player_absence(team, p, window, games, "CALLED_UP")

    def covid_outbreak_players(self, team: Team, window: DateWindow, games: List[Game]) -> None:
        roster = self.rosters_by_team_id.get(team.id, [])
        if not roster:
            return
        n = self.rng.randint(self.cfg.covid_players_min, min(self.cfg.covid_players_max, len(roster)))
        picked = self.rng.sample(roster, n)
        self.log.add("COVID_PLAYERS", f"{team.name}: {n} players OUT {window[0]}..{window[1]}")
        for p in picked:
            self.mark_player_absent(p.id, window, "COVID")
            self._tag_games_with_player_absence(team, p, window, games, "COVID")

    @staticmethod
    def _tag_games_with_player_absence(team: Team, player: Player,
                                       window: DateWindow, games: List[Game], reason: str) -> None:
        a, b = window
        for g in games:
            if not g.slot:
                continue
            if not (a <= g.slot.date <= b):
                continue
            if g.home.id != team.id and g.away.id != team.id:
                continue
            g.notes.append(f"PLAYER_OUT:{team.name}:{player.name}:{reason}:{a}->{b}")

    # ===== Existing events (team/venue) =====

    def team_unavailable(
        self,
        team: Team,
        window: DateWindow,
        games: List[Game],
        *,
        reschedule_end: Optional[date] = None
    ) -> None:
        a, b = window
        affected = [
            g for g in games
            if g.slot
            and (g.home.id == team.id or g.away.id == team.id)
            and a <= g.slot.date <= b
        ]

        self.log.add("TEAM_UNAVAILABLE", f"{team.name} unavailable in {a}..{b}. affected={len(affected)}")

        for g in affected:
            old = g.slot
            ok = self.scheduler.reschedule_game_forward(
                g,
                allow_any_weekday=True,
                allow_alternate_venues=True,
                end_date=reschedule_end
            )
            if ok:
                self._post_notes(g)
                self.log.add("RESCHEDULE", f"{g.home.name} vs {g.away.name} moved {old.date} -> {g.slot.date}",
                             game_id=g.id)
            else:
                self.log.add("RESCHEDULE_FAIL", f"Could not reschedule {g.home.name} vs {g.away.name} (was {old.date})",
                             game_id=g.id)

    def venue_blocked(
        self,
        venue: Venue,
        window: DateWindow,
        games: List[Game],
        *,
        reschedule_end: Optional[date] = None
    ) -> None:
        a, b = window
        affected = [
            g for g in games
            if g.slot
            and g.venue.id == venue.id
            and a <= g.slot.date <= b
        ]

        self.log.add("VENUE_BLOCKED", f"{venue.name} blocked in {a}..{b}. affected={len(affected)}")

        for g in affected:
            old = g.slot
            ok = self.scheduler.reschedule_game_forward(
                g,
                allow_any_weekday=True,
                allow_alternate_venues=True,
                end_date=reschedule_end
            )
            if ok:
                self._post_notes(g)
                self.log.add(
                    "RESCHEDULE",
                    f"{g.home.name} vs {g.away.name} moved {old.date} -> {g.slot.date} (venue {g.venue.name})",
                    game_id=g.id
                )
            else:
                self.log.add("RESCHEDULE_FAIL", f"Could not reschedule {g.home.name} vs {g.away.name} (was {old.date})",
                             game_id=g.id)

    def concert_for_game(self, g: Game, primary_venue: Venue, *, reschedule_end=None) -> None:
        if g.slot is None:
            return

        old_slot = g.slot
        self.log.add(
            "CONCERT",
            f"Concert at {primary_venue.name} on {old_slot.date} {old_slot.start.strftime('%H:%M')}",
            game_id=g.id
        )

        # secondary venue if exists
        vlist = self.scheduler.venues_by_team.get(g.home.id, [])
        secondary = None
        if len(vlist) >= 2:
            for v in vlist:
                if v.id != primary_venue.id:
                    secondary = v
                    break

        # 1) try move to secondary venue same slot
        if secondary is not None:
            self.scheduler.cal.unreserve(primary_venue.id, (g.home.id, g.away.id), old_slot)

            if self.scheduler.is_resource_free(old_slot, secondary.id, (g.home.id, g.away.id)):
                g.venue = secondary
                g.slot = old_slot
                self.scheduler.cal.reserve(secondary.id, (g.home.id, g.away.id), old_slot)
                g.notes.append("CONCERT_MOVE_TO_SECONDARY_VENUE")
                self.log.add("VENUE_CHANGE", f"Moved to secondary venue: {secondary.name}", game_id=g.id)
                self._post_notes(g)
                return

            self.scheduler.cal.reserve(primary_venue.id, (g.home.id, g.away.id), old_slot)

        # 2) fallback: reschedule
        ok = self.scheduler.reschedule_game_forward(
            g,
            allow_any_weekday=True,
            allow_alternate_venues=True,
            end_date=reschedule_end
        )
        if ok:
            g.notes.append("CONCERT_RESCHEDULE")
            self.log.add(
                "RESCHEDULE",
                f"Concert forced reschedule to {g.slot.date} {g.slot.start.strftime('%H:%M')} @ {g.venue.name}",
                game_id=g.id
            )
            self._post_notes(g)
        else:
            self.log.add("RESCHEDULE_FAIL", "Concert: could not reschedule game", game_id=g.id)

    def maybe_concert_event(self, games: List[Game], current_day: date, *, reschedule_end=None) -> None:
        day_games = [g for g in games if g.slot and g.slot.date == current_day]

        candidates = []
        for g in day_games:
            vlist = self.scheduler.venues_by_team.get(g.home.id, [])
            if not vlist:
                continue
            primary = vlist[0]
            if g.venue.id == primary.id:
                candidates.append(g)

        if not candidates:
            return

        g = self.rng.choice(candidates)
        self.concert_for_game(g, g.venue, reschedule_end=reschedule_end)

    @staticmethod
    def _post_notes(game: Game) -> None:
        game.notes.append("NOTE: If scheduled during national team windows, teams may play without called-up players.")
        game.notes.append("NOTE: If rescheduled after transfer period, eligibility uses roster as of ORIGINAL scheduled date.")
