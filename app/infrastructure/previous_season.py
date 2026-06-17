from __future__ import annotations
from typing import List
from app.domain.team import Team


def previous_season_order_names() -> List[str]:
    # 1..16 final order after last season play-off/play-out
    return [
        "U-BT Cluj-Napoca",
        "CSM CSU Oradea",
        "CSO Voluntari",
        "CS Valcea 1924",
        "FC Arges Pitesti",
        "SCM Politehnica Timisoara",
        "CSM Corona Brasov",
        "SCMU Craiova",
        "Rapid Bucuresti",
        "CSM Targu Mures",
        "CSU Sibiu",
        "Dinamo Bucuresti",
        "CSA Steaua Sharks Bucuresti",
        "CSM BBA Petrolul Ploiesti",
        "CSM Targu Jiu",
        "CSM Galati",
    ]


def previous_cup_winner_name() -> str:
    return "U-BT Cluj-Napoca"


def resolve_previous_season_order(current_teams: List[Team]) -> List[Team]:
    by_name = {t.name: t for t in current_teams}
    order = []
    for name in previous_season_order_names():
        if name not in by_name:
            raise ValueError(f"Team from previous season missing in current data: {name}")
        order.append(by_name[name])
    return order


def resolve_previous_cup_winner(current_teams: List[Team]) -> Team:
    by_name = {t.name: t for t in current_teams}
    name = previous_cup_winner_name()
    if name not in by_name:
        raise ValueError(f"Previous cup winner missing in current data: {name}")
    return by_name[name]
