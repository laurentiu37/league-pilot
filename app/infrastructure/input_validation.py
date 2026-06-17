from __future__ import annotations
from typing import Dict, List
from app.domain.team import Team
from app.domain.venue import Venue


def validate_teams_and_venues(teams: List[Team], venues_by_team: Dict[str, List[Venue]]) -> None:
    if len(teams) != 16:
        raise ValueError(f"Campionatul trebuie sa aiba exact 16 echipe, nu {len(teams)}")

    seen = set()
    for t in teams:
        if t.name in seen:
            raise ValueError(f"Echipa duplicata: {t.name}")
        seen.add(t.name)

        if t.id not in venues_by_team or len(venues_by_team[t.id]) == 0:
            raise ValueError(f"Echipa {t.name} nu are nicio sala asociata")


def validate_previous_season(prev_names: List[str], current_teams: List[Team]) -> None:
    curr = {t.name for t in current_teams}
    missing = [name for name in prev_names if name not in curr]
    if missing:
        raise ValueError(f"Echipe din sezonul anterior lipsa in sezonul curent: {missing}")


def validate_rosters(rosters_by_team_name: Dict[str, List], teams: List[Team]) -> None:
    """Validate that every team has a roster and basic player fields look sane."""
    team_names = {t.name for t in teams}
    roster_names = set(rosters_by_team_name.keys())

    missing = sorted(team_names - roster_names)
    extra = sorted(roster_names - team_names)

    if missing:
        raise ValueError(f"Lipsesc roster-ele pentru echipele: {missing}")
    if extra:
        raise ValueError(f"Roster definit pentru echipe care nu exista in campionat: {extra}")

    for team_name, roster in rosters_by_team_name.items():
        if not isinstance(roster, list) or len(roster) == 0:
            raise ValueError(f"Roster gol pentru echipa: {team_name}")

        seen_players = set()
        for p in roster:
            pname = getattr(p, "name", None) if not isinstance(p, dict) else p.get("name")
            ppos = getattr(p, "pos", None) if not isinstance(p, dict) else p.get("pos")
            ph = getattr(p, "height_cm", None) if not isinstance(p, dict) else p.get("height_cm")

            if not pname or not isinstance(pname, str):
                raise ValueError(f"Jucator invalid (name) la {team_name}: {p}")
            if pname in seen_players:
                raise ValueError(f"Jucator duplicat in {team_name}: {pname}")
            seen_players.add(pname)

            if not ppos or not isinstance(ppos, str):
                raise ValueError(f"Jucator invalid (pos) la {team_name}: {pname}")
            if not isinstance(ph, int) or ph < 160 or ph > 230:
                raise ValueError(f"Inaltime suspecta la {team_name} / {pname}: {ph}")
