from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from app.domain.timeslot import TimeSlot


@dataclass
class CalendarStore:
    # venue_id -> list of TimeSlot
    venue_busy: Dict[str, List[TimeSlot]] = field(default_factory=dict)
    # team_id -> list of TimeSlot
    team_busy: Dict[str, List[TimeSlot]] = field(default_factory=dict)

    # --- Overlap rules ---
    # VENUE: conflict doar daca e aceeasi zi si aceeasi ora (permite 2 meciuri/zi la ore diferite -> Final8 OK)
    @staticmethod
    def _venue_overlaps(a: TimeSlot, b: TimeSlot) -> bool:
        return a.date == b.date and a.start == b.start

    # TEAM: conflict daca e aceeasi zi (o echipa nu joaca de 2 ori intr-o zi)
    @staticmethod
    def _team_overlaps(a: TimeSlot, b: TimeSlot) -> bool:
        return a.date == b.date

    def is_venue_free(self, venue_id: str, slot: TimeSlot) -> bool:
        for s in self.venue_busy.get(venue_id, []):
            if self._venue_overlaps(s, slot):
                return False
        return True

    def is_team_free(self, team_id: str, slot: TimeSlot) -> bool:
        for s in self.team_busy.get(team_id, []):
            if self._team_overlaps(s, slot):
                return False
        return True

    def reserve(self, venue_id: str, team_ids: Tuple[str, str], slot: TimeSlot) -> None:
        self.venue_busy.setdefault(venue_id, []).append(slot)
        for t in team_ids:
            self.team_busy.setdefault(t, []).append(slot)

    def unreserve(self, venue_id: str, team_ids: Tuple[str, str], slot: TimeSlot) -> None:
        if venue_id in self.venue_busy:
            self.venue_busy[venue_id] = [s for s in self.venue_busy[venue_id] if not self._venue_overlaps(s, slot)]
        for t in team_ids:
            if t in self.team_busy:
                self.team_busy[t] = [s for s in self.team_busy[t] if not self._team_overlaps(s, slot)]
