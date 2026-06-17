from datetime import date

# Season window
SEASON_START = date(2026, 10, 1)
SEASON_END = date(2027, 6, 15)

CUP_Q1_START = date(2026, 9, 20)
CUP_Q1_END = date(2026, 9, 27)

CUP_Q2_START = date(2026, 12, 17)
CUP_Q2_END = date(2026, 12, 23)

# National team breaks (games allowed, but note: without called-up players)
NATIONAL_TEAM_BREAKS = [
    (date(2026, 11, 10), date(2026, 11, 20)),
    (date(2027, 2, 15), date(2027, 2, 25)),
]

# Cup / playoff key dates (example; adjust as you like)
CUP_QUALIFIERS_START = date(2027, 1, 10)
CUP_FINAL8_DAY1 = date(2027, 2, 10)  # Day1 QF1+QF2

PLAYOFF_START = date(2027, 5, 2)

# Supercup (before season)
SUPERCUP_DAY = date(2026, 9, 10)
