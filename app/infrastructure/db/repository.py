# db/repository.py
from __future__ import annotations
from datetime import datetime
import math
import pandas as pd

from sqlalchemy.orm import Session

from app.infrastructure.db.models import Run, GameRow, PlayerStatRow, FinalOrderRow
from app.infrastructure.exporter import Exporter

def is_empty(value):
    if value is None:
        return True
    try:
        return pd.isna(value)
    except Exception:
        return False


def clean_score(value):
    if is_empty(value):
        return None
    return int(value)


def clean_str(value):
    if is_empty(value):
        return ""
    return str(value)

def save_run(session: Session, result) -> int:
    # supercup winner
    sc = result.supercup_game
    sc_winner = None
    if sc.home_score is not None and sc.away_score is not None:
        sc_winner = sc.home.name if sc.home_score > sc.away_score else sc.away.name

    run = Run(
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        seed=result.seed,
        cup_winner=result.cup_winner.name,
        champion=result.final_order[0].name,
        vice=result.final_order[1].name,
        supercup_winner=sc_winner,
        events_log=result.log_text,
    )
    session.add(run)
    session.flush()  # run.id

    # final order 1..16
    for i, t in enumerate(result.final_order, start=1):
        session.add(FinalOrderRow(run_id=run.id, rank=i, team=t.name))

    # games
    df_games = Exporter.games_to_dataframe(result.all_games)
    for row in df_games.to_dict(orient="records"):
        g = GameRow(
            run_id=run.id,
            stage=clean_str(row.get("stage")),
            label=clean_str(row.get("label")),
            date=None if is_empty(row.get("date")) else datetime.fromisoformat(row["date"]).date(),
            time=None if is_empty(row.get("time")) else datetime.strptime(row["time"], "%H:%M").time(),
            home=clean_str(row.get("home")),
            away=clean_str(row.get("away")),
            home_score=clean_score(row.get("home_score")),
            away_score=clean_score(row.get("away_score")),
            venue=clean_str(row.get("venue")),
            tv_featured=bool(row.get("tv_featured")),
            tv_requested_time=None if is_empty(row.get("tv_requested_time")) else datetime.strptime(
                row["tv_requested_time"], "%H:%M").time(),
            tv_confirmed=bool(row.get("tv_confirmed")),
            notes=clean_str(row.get("notes")),
        )
        session.add(g)

    # player averages report (per competition)
    df_players = Exporter.player_averages_to_dataframe(result.all_games, result.rosters_by_team_id)
    for row in df_players.to_dict(orient="records"):
        ps = PlayerStatRow(
            run_id=run.id,
            stage="",  # optional
            label="",
            date=None,
            competition=row.get("competition") or "",
            player_id=row.get("player_id") or "",
            player_name=row.get("player_name") or "",
            position=row.get("position") or "",
            team=row.get("team") or "",
            games_played=int(row.get("games_played") or 0),
            pts_avg=str(row.get("pts_avg")),
            reb_avg=str(row.get("reb_avg")),
            ast_avg=str(row.get("ast_avg")),
            min_avg=str(row.get("min_avg")),
        )
        session.add(ps)

    session.commit()
    return run.id
