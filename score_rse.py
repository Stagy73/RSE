# score_rse.py

def calcul_score_rse(row):
    """
    Score de cohérence RSE
    N'influence PAS (V,F)
    Sert uniquement à classer les chevaux du schéma
    """

    score = 0

    # -----------------
    # MARCHÉ (cote saine)
    # -----------------
    if "COTE" in row:
        if 3.0 <= row["COTE"] <= 12.0:
            score += 2
        elif row["COTE"] > 12.0:
            score += 1

    # -----------------
    # REPOS OPTIMAL
    # -----------------
    if "Repos" in row:
        if 7 <= row["Repos"] <= 21:
            score += 2
        elif row["Repos"] <= 30:
            score += 1

    # -----------------
    # ACTIF / STABILITÉ
    # -----------------
    if "Actif" in row and row["Actif"] == 1:
        score += 1

    return score
