def compute_strength_from_previous_season(prev_order):
    """
    coeficienti calculati pe baza clasarii din sezonul anterior.
    - top avantajat ca sa simuleze realitatea
    - coada clasamentului e penalizata puternic pentru a arata diferentele clare din realitate
    - diferentele vor sa arate realitatea
    """

    n = len(prev_order)

    maxx = 1.35   # campioana
    minn = 0.70   # ultima

    strengths = {}

    for i, team in enumerate(prev_order):
        rank = i / (n - 1)  # 0 (campioana) → 1 (ultima)

        coef = maxx - (rank ** 1.8) * (maxx - minn)

        # bonus mic pentru Top 4
        if i < 4:
            coef *= 1.07

        strengths[team.id] = round(coef, 3)

    return strengths
