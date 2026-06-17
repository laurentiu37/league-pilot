from __future__ import annotations

from datetime import date, timedelta, time
from typing import Dict, List, Optional, Tuple
import random

from app.domain.team import Team
from app.domain.venue import Venue
from app.domain.timeslot import TimeSlot
from app.domain.game import Game
from .constraints import Constraints
from .calendar_store import CalendarStore
from app.events.event_log import EventLog

DateWindow = Tuple[date, date]


class Scheduler:
    def __init__(
        self,
        teams: List[Team],
        venues: List[Venue],
        constraints: Constraints,
        match_duration_hours: int = 2,
        time_slots: Optional[List[time]] = None,
        season_end: Optional[date] = None,
        seed: Optional[int] = None,
        event_log: Optional[EventLog] = None,
    ):
        self.teams = teams
        self.venues = venues
        self.constraints = constraints
        self.match_duration_hours = match_duration_hours
        self.time_slots = time_slots or [time(17, 0), time(19, 30)]
        self.season_end = season_end or date.today()
        self.rng = random.Random(seed)
        self.log = event_log

        self.cal = CalendarStore()
        for v in venues:
            self.cal.venue_busy.setdefault(v.id, [])
        for t in teams:
            self.cal.team_busy.setdefault(t.id, [])

        # helpful lookup
        self.venues_by_id: Dict[str, Venue] = {v.id: v for v in venues}
        self.venues_by_team: Dict[str, List[Venue]] = {}
        for v in venues:
            self.venues_by_team.setdefault(v.home_team_id, []).append(v)

    def is_resource_free(self, slot: TimeSlot, venue_id: str, teams: Tuple[str, str], *,
                         ignore_hard_blocks: bool = False) -> bool:
        if (not ignore_hard_blocks) and self.constraints.is_hard_blocked(slot.date):
            return False
        if not self.cal.is_venue_free(venue_id, slot):
            return False
        if not self.cal.is_team_free(teams[0], slot):
            return False
        if not self.cal.is_team_free(teams[1], slot):
            return False
        return True

    def reserve(self, slot: TimeSlot, venue_id: str, teams: Tuple[str, str]) -> None:
        self.cal.reserve(venue_id, teams, slot)

    def unreserve_game(self, game: Game) -> None:
        if game.slot is None:
            return
        self.cal.unreserve(game.venue.id, (game.home.id, game.away.id), game.slot)
        game.slot = None

    def schedule_game_in_window(
            self,
            game: Game,
            window: DateWindow,
            preferred_weekdays: Optional[List[int]] = None,  # Monday=0..Sunday=6
            allow_alternate_venues: bool = True,
            randomize: bool = True,
            ignore_hard_blocks: bool = False,
    ) -> bool:
        start, end = window
        if end > self.season_end:
            end = self.season_end
        if start > end:
            return False

        # venue candidates
        venue_candidates = [game.venue]
        if allow_alternate_venues:
            venue_candidates = self.venues_by_team.get(game.home.id, [game.venue])

        days = (end - start).days
        date_list = [start + timedelta(days=i) for i in range(days + 1)]

        if preferred_weekdays is not None:
            date_list = [d for d in date_list if d.weekday() in preferred_weekdays]

        if randomize:
            self.rng.shuffle(date_list)

        time_list = self.time_slots[:]
        if randomize:
            self.rng.shuffle(time_list)

        for d in date_list:
            if (not ignore_hard_blocks) and self.constraints.is_hard_blocked(d):
                continue
            for t in time_list:
                slot = TimeSlot(date=d, start=t, duration_hours=self.match_duration_hours)
                for v in venue_candidates:
                    if self.is_resource_free(slot, v.id, (game.home.id, game.away.id),
                                             ignore_hard_blocks=ignore_hard_blocks):
                        game.slot = slot
                        if game.original_slot is None:
                            game.original_slot = slot
                        game.venue = v
                        self.reserve(slot, v.id, (game.home.id, game.away.id))

                        if self.log:
                            self.log.add(
                                "SCHEDULE",
                                f"{game.stage} {game.label}: {game.home.name} vs {game.away.name} -> {slot.date} {slot.start.strftime('%H:%M')} @ {v.name}",
                                game_id=game.id
                            )
                        return True
        return False

    def reschedule_game_forward(
            self,
            game: Game,
            allow_any_weekday: bool = True,
            allow_alternate_venues: bool = True,
            end_date: Optional[date] = None,
    ) -> bool:
        if game.slot is None:
            return False

        old = game.slot
        start_date = old.date + timedelta(days=1)

        # limita de cautare
        limit = end_date or self.season_end
        if limit > self.season_end:
            limit = self.season_end

        # unreserve old
        self.cal.unreserve(game.venue.id, (game.home.id, game.away.id), old)
        game.slot = None

        preferred = None if allow_any_weekday else [4, 5, 6]

        ok = self.schedule_game_in_window(
            game,
            (start_date, limit),
            preferred_weekdays=preferred,
            allow_alternate_venues=allow_alternate_venues,
            randomize=True,
            ignore_hard_blocks=False
        )

        if not ok:
            # restore old
            game.slot = old
            self.reserve(old, game.venue.id, (game.home.id, game.away.id))
            if self.log:
                self.log.add(
                    "RESCHEDULE_FAIL",
                    f"{game.stage} {game.label}: could not find new slot after {start_date} (limit={limit})",
                    game_id=game.id
                )
            return False

        if self.log:
            assert game.slot is not None
            self.log.add(
                "RESCHEDULE",
                f"{game.stage} {game.label}: moved to {game.slot.date} {game.slot.start.strftime('%H:%M')} @ {game.venue.name}",
                game_id=game.id
            )
        return True

    def try_change_start_time(self, game: Game, allowed_times: List[time]) -> bool:
        # TV soft constraint: change ONLY start time, same day/venue
        if game.slot is None:
            return False

        old_slot = game.slot

        # copiem si randomizzm
        candidate_times = allowed_times[:]
        self.rng.shuffle(candidate_times)

        # scoatem rezervarea veche temporar
        self.cal.unreserve(game.venue.id, (game.home.id, game.away.id), old_slot)

        for t in candidate_times:
            new_slot = TimeSlot(date=old_slot.date, start=t, duration_hours=old_slot.duration_hours)

            if self.is_resource_free(new_slot, game.venue.id, (game.home.id, game.away.id)):
                game.slot = new_slot
                game.tv_requested_time = t
                self.reserve(new_slot, game.venue.id, (game.home.id, game.away.id))
                game.tv_confirmed = True

                if self.log:
                    self.log.add(
                        "TV_TIME_CHANGE_OK",
                        f"{game.home.name} vs {game.away.name}: {old_slot.start.strftime('%H:%M')} -> {t.strftime('%H:%M')}",
                        game_id=game.id
                    )
                return True

        # restore daca nu merge niciuna
        game.slot = old_slot
        self.reserve(old_slot, game.venue.id, (game.home.id, game.away.id))
        game.tv_confirmed = False

        if self.log:
            self.log.add(
                "TV_TIME_CHANGE_FAIL",
                f"{game.home.name} vs {game.away.name}: no allowed TV time free",
                game_id=game.id
            )
        return False
