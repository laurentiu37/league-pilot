from __future__ import annotations
from typing import List, Dict
import pandas as pd

from app.domain.game import Game
from app.domain.player import Player
from app.domain.standings import StandingsRow


class Exporter:
    @staticmethod
    def games_to_dataframe(games: List[Game]) -> pd.DataFrame:
        rows = []
        for g in games:
            rows.append({
                "stage": g.stage,
                "label": g.label,
                "date": g.slot.date.isoformat() if g.slot else None,
                "time": g.slot.start.strftime("%H:%M") if g.slot else None,
                "home": g.home.name,
                "away": g.away.name,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "venue": g.venue.name if g.venue else None,
                "tv_featured": g.tv_featured,
                "tv_requested_time": g.tv_requested_time.strftime("%H:%M") if g.tv_requested_time else None,
                "tv_confirmed": g.tv_confirmed,
                "notes": " | ".join(g.notes) if g.notes else ""
            })
        return pd.DataFrame(rows)

    @staticmethod
    def standings_to_dataframe(table: List[StandingsRow]) -> pd.DataFrame:
        rows = []
        for i, r in enumerate(table, start=1):
            rows.append({
                "position": i,
                "team": r.team.name,
                "points": r.points,
                "wins": r.wins,
                "losses": r.losses,
                "pf": r.pf,
                "pa": r.pa,
                "diff": r.diff,
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _competition_of_stage(stage: str) -> str:
        s = (stage or "").upper()
        if s in ("CUP_Q", "CUP_FINAL8"):
            return "CUPA"
        if s == "SUPERCUP":
            return "SUPERCUPA"
        if s in ("REGULAR", "PLAYOFF"):
            return "CAMPIONAT"
        return s or "UNKNOWN"

    @staticmethod
    def player_averages_to_dataframe(
        games: List[Game],
        rosters_by_team_id: Dict[str, List[Player]],
        *,
        include_only_played: bool = True,
    ) -> pd.DataFrame:
        # key = "COMP::player_id"
        agg: Dict[str, Dict[str, int]] = {}

        # player lookup
        player_by_id: Dict[str, Player] = {}
        for _tid, roster in rosters_by_team_id.items():
            for p in roster:
                player_by_id[p.id] = p

        for g in games:
            if include_only_played and not g.played:
                continue
            if not g.player_stats:
                continue

            comp = Exporter._competition_of_stage(g.stage)

            for pid, st in g.player_stats.items():
                pname = player_by_id.get(pid).name if pid in player_by_id else pid
                pos = player_by_id.get(pid).pos if pid in player_by_id else ""
                team_name = str(st.get("team_name", ""))

                key = f"{comp}::{pid}"
                if key not in agg:
                    agg[key] = {
                        "competition": comp,
                        "player_id": pid,
                        "player_name": pname,
                        "position": pos,
                        "team": team_name,
                        "games_played": 0,
                        "pts": 0,
                        "reb": 0,
                        "ast": 0,
                        "min": 0,
                    }

                row = agg[key]
                row["games_played"] = int(row["games_played"]) + 1
                row["pts"] = int(row["pts"]) + int(st.get("pts", 0))
                row["reb"] = int(row["reb"]) + int(st.get("reb", 0))
                row["ast"] = int(row["ast"]) + int(st.get("ast", 0))
                row["min"] = int(row["min"]) + int(st.get("min", 0))

        rows = []
        for row in agg.values():
            gp = int(row["games_played"])
            if gp <= 0:
                continue
            rows.append({
                **row,
                "pts_avg": round(int(row["pts"]) / gp, 2),
                "reb_avg": round(int(row["reb"]) / gp, 2),
                "ast_avg": round(int(row["ast"]) / gp, 2),
                "min_avg": round(int(row["min"]) / gp, 2),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        return df.sort_values(
            by=["competition", "pts_avg", "reb_avg", "ast_avg", "player_name"],
            ascending=[True, False, False, False, True],
            kind="mergesort",
        )

    @staticmethod
    def export_csv(df: pd.DataFrame, filename: str) -> None:
        df.to_csv(filename, index=False, encoding="utf-8")
