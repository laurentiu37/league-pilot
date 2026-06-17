from __future__ import annotations

import io
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.infrastructure.db.database import SessionLocal
from app.infrastructure.db.repository_read import get_run, get_games, get_player_avgs, get_final_order

router = APIRouter(prefix="/runs/{run_id}/export", tags=["export"])


def _csv_response(df: pd.DataFrame, filename: str) -> StreamingResponse:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    bio = io.BytesIO(buf.getvalue().encode("utf-8-sig"))  # utf-8-sig pt Excel RO
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(bio, media_type="text/csv", headers=headers)


def _txt_response(text: str, filename: str) -> StreamingResponse:
    bio = io.BytesIO(text.encode("utf-8"))
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(bio, media_type="text/plain", headers=headers)


@router.get("/games.csv")
def export_games_csv(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        games = get_games(session, run_id)
        rows = []
        for g in games:
            rows.append({
                "stage": g.stage,
                "label": g.label,
                "date": g.date.isoformat() if g.date else None,
                "time": g.time.strftime("%H:%M") if g.time else None,
                "home": g.home,
                "away": g.away,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "venue": g.venue,
                "tv_featured": g.tv_featured,
                "tv_requested_time": g.tv_requested_time.strftime("%H:%M") if g.tv_requested_time else None,
                "tv_confirmed": g.tv_confirmed,
                "notes": g.notes,
            })

        # sortare
        rows.sort(key=lambda x: (x["date"] or "9999-12-31", x["time"] or "23:59", x["stage"], x["label"]))
        df = pd.DataFrame(rows)
        return _csv_response(df, f"run_{run_id}_games.csv")


@router.get("/players_avg.csv")
def export_players_avg_csv(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        stats = get_player_avgs(session, run_id)
        rows = []
        for s in stats:
            rows.append({
                "competition": s.competition,
                "player_id": s.player_id,
                "player_name": s.player_name,
                "position": s.position,
                "team": s.team,
                "games_played": s.games_played,
                "pts_avg": s.pts_avg,
                "reb_avg": s.reb_avg,
                "ast_avg": s.ast_avg,
                "min_avg": s.min_avg,
            })

        df = pd.DataFrame(rows)
        return _csv_response(df, f"run_{run_id}_players_avg.csv")


@router.get("/events.txt")
def export_events_txt(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        text = r.events_log or ""
        return _txt_response(text, f"run_{run_id}_events.txt")


@router.get("/regular_standings.csv")
def export_regular_standings_csv(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        games = get_games(session, run_id)

        table = {}

        def ensure(team: str):
            table.setdefault(team, {"team": team, "wins": 0, "losses": 0, "pf": 0, "pa": 0})

        for g in games:
            if g.stage != "REGULAR":
                continue
            if g.home_score is None or g.away_score is None:
                continue

            ensure(g.home)
            ensure(g.away)

            hs = int(g.home_score)
            as_ = int(g.away_score)

            table[g.home]["pf"] += hs
            table[g.home]["pa"] += as_
            table[g.away]["pf"] += as_
            table[g.away]["pa"] += hs

            if hs > as_:
                table[g.home]["wins"] += 1
                table[g.away]["losses"] += 1
            else:
                table[g.away]["wins"] += 1
                table[g.home]["losses"] += 1

        rows = list(table.values())
        for row in rows:
            row["diff"] = row["pf"] - row["pa"]

        # sort: wins desc, diff desc, pf desc, team asc
        rows.sort(key=lambda x: (-x["wins"], -x["diff"], -x["pf"], x["team"]))

        for i, row in enumerate(rows, start=1):
            row["rank"] = i

        df = pd.DataFrame(rows, columns=["rank", "team", "wins", "losses", "pf", "pa", "diff"])
        return _csv_response(df, f"run_{run_id}_regular_standings.csv")


@router.get("/final_order.csv")
def export_final_order_csv(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        fo = get_final_order(session, run_id)
        if not fo:
            raise HTTPException(
                status_code=404,
                detail="Final order not found for this run (run a new simulation after DB update)"
            )

        rows = [{"rank": x.rank, "team": x.team} for x in fo]
        df = pd.DataFrame(rows, columns=["rank", "team"])
        return _csv_response(df, f"run_{run_id}_final_order.csv")
