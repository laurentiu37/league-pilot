from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import time
import secrets

from app.api.schemas import SimulateRequest, SimulateResponse
from app.use_cases.simulate_season import simulate_season, SimulateSeasonParams

from app.infrastructure.db.database import SessionLocal, engine, Base
from app.infrastructure.db.repository import save_run
from app.infrastructure.db.repository_read import list_runs, get_run, get_games, get_player_avgs
from app.api.exports import router as export_router
from app.api import store

app = FastAPI(title="League Simulator API", version="0.1")


app.include_router(export_router)


@app.on_event("startup")
def on_startup():
    # creeaza tabelele doar cand porneste app
    Base.metadata.create_all(bind=engine)


# pentru UI React pe localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "https://frontend-production-dce1.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_hhmm(s: str) -> time:
    try:
        hh, mm = s.strip().split(":")
        return time(int(hh), int(mm))
    except Exception:
        raise ValueError(f"Invalid time format '{s}', expected HH:MM")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    # parser pentru time slot uri
    try:
        slots = [parse_hhmm(x) for x in req.time_slots]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        tv_time = parse_hhmm(req.tv_requested_time) if req.tv_requested_time else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    seed = req.seed if (req.seed is not None and req.seed != 0) else secrets.randbelow(32_147_483_647)

    tv_allowed = [parse_hhmm(x) for x in req.tv_allowed_times] if req.tv_allowed_times else None

    params = SimulateSeasonParams(
        seed=seed,
        p_covid_per_round=req.p_covid_per_round,
        p_venue_block_per_round=req.p_venue_block_per_round,
        p_concert_per_round=req.p_concert_per_round,
        p_injury_per_round=req.p_injury_per_round,
        p_callup_per_round=req.p_callup_per_round,
        p_covid_player_outbreak_per_round=req.p_covid_player_outbreak_per_round,
        time_slots=slots,
        tv_featured_per_round=req.tv_featured_per_round,
        tv_requested_time=tv_time,
        tv_allowed_times=tv_allowed,
    )

    result = simulate_season(params)

    with SessionLocal() as session:
        run_id = save_run(session, result)

    return SimulateResponse(run_id=run_id, message="Simulation completed", seed=seed)


@app.get("/runs")
def runs():
    with SessionLocal() as session:
        items = list_runs(session, limit=50)
        return {
            "rows": [
                {
                    "run_id": r.id,
                    "created_at": r.created_at,
                    "seed": r.seed,
                    "cup_winner": r.cup_winner,
                    "champion": r.champion,
                    "vice": r.vice,
                    "supercup_winner": r.supercup_winner,
                }
                for r in items
            ]
        }


@app.get("/runs/{run_id}/summary")
def run_summary_db(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")
        return {
            "run_id": r.id,
            "created_at": r.created_at,
            "seed": r.seed,
            "cup_winner": r.cup_winner,
            "champion": r.champion,
            "vice": r.vice,
            "supercup_winner": r.supercup_winner,
            "games_count": len(r.games),
        }


@app.get("/runs/{run_id}/games")
def run_games_db(run_id: int):
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

        # sortare dupa data disputarii
        rows.sort(key=lambda x: (x["date"] or "9999-12-31", x["time"] or "23:59", x["stage"], x["label"]))
        return {"run_id": run_id, "rows": rows}


@app.get("/runs/{run_id}/players-avg")
def run_players_avg_db(run_id: int):
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
        return {"run_id": run_id, "rows": rows}


@app.get("/runs/{run_id}/events")
def run_events_db(run_id: int):
    with SessionLocal() as session:
        r = get_run(session, run_id)
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"run_id": run_id, "log": r.events_log}


@app.delete("/runs")
def clear_runs():
    store.clear_all_runs()
    return {"ok": True}
