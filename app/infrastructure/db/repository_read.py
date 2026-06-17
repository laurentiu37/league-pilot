# db/repository_read.py
from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.infrastructure.db.models import Run, GameRow, PlayerStatRow, FinalOrderRow


def list_runs(session: Session, limit: int = 50):
    stmt = select(Run).order_by(Run.id.desc()).limit(limit)
    return session.execute(stmt).scalars().all()


def get_run(session: Session, run_id: int) -> Run | None:
    stmt = select(Run).where(Run.id == run_id)
    return session.execute(stmt).scalar_one_or_none()


def get_games(session: Session, run_id: int):
    stmt = select(GameRow).where(GameRow.run_id == run_id)
    return session.execute(stmt).scalars().all()


def get_player_avgs(session: Session, run_id: int):
    stmt = select(PlayerStatRow).where(PlayerStatRow.run_id == run_id)
    return session.execute(stmt).scalars().all()


def get_final_order(session: Session, run_id: int):
    stmt = select(FinalOrderRow).where(FinalOrderRow.run_id == run_id).order_by(FinalOrderRow.rank.asc())
    return session.execute(stmt).scalars().all()
