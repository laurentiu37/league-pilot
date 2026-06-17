from __future__ import annotations
from typing import Dict, List, Tuple
from app.domain.team import Team
from app.domain.venue import Venue


def load_teams_and_venues() -> Tuple[List[Team], List[Venue], Dict[str, List[Venue]]]:
    # IMPORTANT: numele din acest fisier trebuie sa corespunda cu numele din previous_season.py
    raw = [
        {"name": "U-BT Cluj-Napoca", "city": "Cluj-Napoca", "venues": ["BT Arena", "Sala Sporturilor Horea Demian"]},
        {"name": "CSM CSU Oradea", "city": "Oradea", "venues": ["Oradea Arena", "Arena Antonio Alexe"]},
        {"name": "CSO Voluntari", "city": "Voluntari", "venues": ["Sala Gabriela Szabo"]},
        {"name": "CS Valcea 1924", "city": "Ramnicu Valcea", "venues": ["Sala Traian"]},
        {"name": "FC Arges Pitesti", "city": "Pitesti", "venues": ["Pitesti Arena"]},
        {"name": "SCM Politehnica Timisoara", "city": "Timisoara", "venues": ["Sala Constantin Jude"]},
        {"name": "CSM Corona Brasov", "city": "Brasov", "venues": ["Sala Sporturilor Dumitru Popescu Colibasi"]},
        {"name": "SCMU Craiova", "city": "Craiova", "venues": ["Sala Polivalenta Craiova"]},
        {"name": "Rapid Bucuresti", "city": "Bucuresti", "venues": ["Sala Rapid"]},
        {"name": "CSM Targu Mures", "city": "Targu Mures", "venues": ["Sala Sporturilor Targu Mures"]},
        {"name": "CSU Sibiu", "city": "Sibiu", "venues": ["Sala Transilvania"]},
        {"name": "Dinamo Bucuresti", "city": "Bucuresti", "venues": ["Sala Dinamo"]},
        {"name": "CSA Steaua Sharks Bucuresti", "city": "Bucuresti", "venues": ["Sala Polivalenta Steaua"]},
        {"name": "CSM BBA Petrolul Ploiesti", "city": "Ploiesti", "venues": ["Sala Olimpia"]},
        {"name": "CSM Targu Jiu", "city": "Targu Jiu", "venues": ["Sala Sporturilor Targu Jiu"]},
        {"name": "CSM Galati", "city": "Galati", "venues": ["Sala Sporturilor Dunarea"]},
    ]

    # create teams and sort alphabetically (initial ranking start)
    teams = [Team(item["name"], city=item["city"]) for item in raw]
    teams.sort(key=lambda x: x.name)

    # build a stable mapping by name to original raw item
    raw_by_name = {item["name"]: item for item in raw}

    venues: List[Venue] = []
    venues_by_team: Dict[str, List[Venue]] = {}

    for t in teams:
        item = raw_by_name[t.name]
        venues_by_team[t.id] = []
        for vname in item["venues"]:
            v = Venue(name=f"{vname} ({item['city']})", home_team_id=t.id)
            venues.append(v)
            venues_by_team[t.id].append(v)

    return teams, venues, venues_by_team
