# db/models.py
from __future__ import annotations
from sqlalchemy import Column, Integer, String, Date, Time, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from .database import Base


class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String, nullable=False)  # simplu pt început; putem face DateTime

    seed = Column(BigInteger, nullable=True)

    cup_winner = Column(String, nullable=False)
    champion = Column(String, nullable=False)
    vice = Column(String, nullable=False)
    supercup_winner = Column(String, nullable=True)

    events_log = Column(Text, nullable=False)

    games = relationship("GameRow", back_populates="run", cascade="all, delete-orphan")
    player_stats = relationship("PlayerStatRow", back_populates="run", cascade="all, delete-orphan")
    final_order = relationship("FinalOrderRow", back_populates="run", cascade="all, delete-orphan")


class GameRow(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, autoincrement=True)

    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    run = relationship("Run", back_populates="games")

    stage = Column(String, nullable=False)
    label = Column(String, nullable=False)

    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)

    home = Column(String, nullable=False)
    away = Column(String, nullable=False)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    venue = Column(String, nullable=True)
    tv_featured = Column(Boolean, nullable=False, default=False)
    tv_requested_time = Column(Time, nullable=True)
    tv_confirmed = Column(Boolean, nullable=False, default=False)

    notes = Column(Text, nullable=False, default="")


class PlayerStatRow(Base):
    __tablename__ = "player_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)

    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    run = relationship("Run", back_populates="player_stats")

    # optional link to game row by index fields (simplu)
    stage = Column(String, nullable=False)
    label = Column(String, nullable=False)
    date = Column(Date, nullable=True)

    player_id = Column(String, nullable=False)
    player_name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    team = Column(String, nullable=False)
    competition = Column(String, nullable=False)

    games_played = Column(Integer, nullable=False)
    pts_avg = Column(String, nullable=False)
    reb_avg = Column(String, nullable=False)
    ast_avg = Column(String, nullable=False)
    min_avg = Column(String, nullable=False)


class FinalOrderRow(Base):
    __tablename__ = "final_order"
    id = Column(Integer, primary_key=True, autoincrement=True)

    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    run = relationship("Run", back_populates="final_order")

    rank = Column(Integer, nullable=False)         # 1..16
    team = Column(String, nullable=False)
