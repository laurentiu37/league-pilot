from datetime import time
from app.use_cases.simulate_season import simulate_season, SimulateSeasonParams
from app.infrastructure.exporter import Exporter


def main():
    result = simulate_season(SimulateSeasonParams(
        seed=None,
        tv_featured_per_round=1,
        time_slots=[time(17, 00), time(17, 15), time(17, 30), time(17, 45),
                    time(18, 00), time(18, 15), time(18, 30), time(18, 45),
                    time(19, 00), time(19, 15), time(19, 30), time(19, 45),
                    time(20, 00), time(20, 15), time(20, 30), time(20, 45), time(21, 00)],
        tv_requested_time=None,
    ))

    # ===== CALENDAR (sortat dupa data disputarii) =====
    df_games = Exporter.games_to_dataframe(result.all_games)
    df_games["_sort_date"] = df_games["date"].fillna("9999-12-31")
    df_games["_sort_time"] = df_games["time"].fillna("23:59")
    df_games = (
        df_games
        .sort_values(by=["_sort_date", "_sort_time", "stage", "label"], kind="mergesort")
        .drop(columns=["_sort_date", "_sort_time"])
    )
    Exporter.export_csv(df_games, "calendar_complet.csv")

    # ===== CLASAMENT =====
    df_reg = Exporter.standings_to_dataframe(result.regular_table)
    Exporter.export_csv(df_reg, "clasament_sezon_regulat.csv")

    # ===== MEDII JUCĂTORI (cu nume) =====
    df_players = Exporter.player_averages_to_dataframe(
        result.all_games,
        result.rosters_by_team_id,
    )
    Exporter.export_csv(df_players, "medii_jucatori_pe_competitii.csv")

    # ===== PRINT WINNERS =====
    # Cupa
    print("Castigatoarea cupei:", result.cup_winner.name)

    # Supercupa
    sc = result.supercup_game
    if sc.home_score is not None and sc.away_score is not None:
        sc_winner = sc.home if sc.home_score > sc.away_score else sc.away
        print("Castigatoarea supercupei:", sc_winner.name)
    else:
        print("Supercupa: neprogramata / nesimulata")

    # Campionat (după playoff/playout final order)
    print("Campioana Romaniei:", result.final_order[0].name)
    print("Vicecampioana Romaniei:", result.final_order[1].name)

    # (opțional) top 3
    print("Locul 3:", result.final_order[2].name)

    # ===== FINAL ORDER (1-16) =====
    with open("final_order_1_16.txt", "w", encoding="utf-8") as f:
        for i, team in enumerate(result.final_order, start=1):
            f.write(f"{i}. {team.name}\n")

    # Logs
    with open("logs_evente.txt", "w", encoding="utf-8") as f:
        f.write(result.log_text)


if __name__ == "__main__":
    main()
