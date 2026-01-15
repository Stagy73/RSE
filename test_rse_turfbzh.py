import pandas as pd
import os
import sys
import random

from cheval import Cheval

# ==================================================
# OUTILS GÉNÉRAUX
# ==================================================
def to_float(val):
    try:
        if val is None:
            return None
        s = str(val).strip().replace(",", ".")
        if s == "" or s.lower() in ["nan", "none", "nc", "na", "-"]:
            return None
        return float(s)
    except:
        return None

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

# ==================================================
# DÉTECTION COLONNES TURFBZH
# ==================================================
def detecter_colonne(df, noms):
    for n in noms:
        if n in df.columns:
            return n
    low = {str(c).lower(): c for c in df.columns}
    for key in noms:
        k = key.lower()
        for cname_low, orig in low.items():
            if k in cname_low:
                return orig
    return None

def extraire_nom_jockey(val):
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() == "nan":
        return None
    if "/" in s:
        s = s.split("/")[0].strip()
    return s

# ==================================================
# SÉLECTION UTILISATEUR
# ==================================================
HIPPODROMES = {
    "1": "cagnes",
    "2": "vincennes",
    "3": "deauville",
    "4": "pau",
    "5": "chantilly",
    "6": "cabourg",
    "7": "fontainebleau",
    "8": None
}

DISCIPLINES = {
    "1": "plat",
    "2": "trot",
    "3": "monte",
    "4": "obstacle"
}

def choisir_hippodrome():
    print("\n🏟️ Choisis l’hippodrome :")
    for k, v in HIPPODROMES.items():
        print(f"{k} - {v if v else 'aucun'}")
    return HIPPODROMES.get(input("👉 Ton choix : ").strip())

def choisir_discipline():
    print("\n🏇 Choisis la discipline :")
    for k, v in DISCIPLINES.items():
        print(f"{k} - {v}")
    return DISCIPLINES.get(input("👉 Ton choix : ").strip())

# ==================================================
# DOMAINES
# ==================================================
DOMAINES = {
    "trot":     {"repos_max": 30, "cote_min": 3.0,  "actif_only": True},
    "monte":    {"repos_max": 21, "cote_min": 5.0,  "actif_only": True},
    "plat":     {"repos_max": 25, "cote_min": 4.0,  "actif_only": True},
    "obstacle": {"repos_max": 60, "cote_min": 10.0, "actif_only": False},
}

SEUILS = {
    "SIGMA_MIN": 55.0,
    "IA_RANK_MAX": 5.0,
    "ELO_MIN": 1400.0,
    "VALUE_COTE_MIN": 6.0
}

# ==================================================
# SCORE RSE
# ==================================================
def calcul_score_rse(row):
    score = 0
    cote = to_float(row.get("COTE"))
    repos = to_float(row.get("Repos"))

    if cote is not None:
        score += 2 if 3 <= cote <= 12 else 1

    if repos is not None:
        score += 2 if 7 <= repos <= 21 else 1

    if row.get("Actif") == 1:
        score += 1

    return score

# ==================================================
# CONFIANCE
# ==================================================
def compter_signaux_ok(c: Cheval):
    return sum([
        c.SIGMA_OK is True,
        c.IA_OK is True,
        c.ELO_OK is True,
        c.VALUE_OK is True
    ])

def calcul_confiance(schema):
    if len(schema) < 2:
        return 0.0

    base, second = schema[0], schema[1]
    gap = clamp((base.score_RSE - second.score_RSE) / 3)
    sig = compter_signaux_ok(base) / 4
    size = clamp(1 - (len(schema) - 2) / 8)

    conf = 0.4 * gap + 0.3 * sig + 0.3 * size
    conf += base.impact_driver()  # 🔥 ELO JOCKEY ici
    return clamp(conf)

# ==================================================
# DÉ PONDÉRÉ
# ==================================================
def tirer_face_ponderee(conf, disc):
    if conf >= 0.75:
        w = [0.35,0.30,0.20,0.10,0.04,0.01]
    elif conf >= 0.5:
        w = [0.20,0.28,0.24,0.18,0.07,0.03]
    else:
        w = [0.06,0.12,0.22,0.25,0.22,0.13]

    if disc == "obstacle":
        w = [x*0.25 for x in w]
        w[3] *= 1.5; w[4] *= 1.8; w[5] *= 2.2

    s = sum(w)
    w = [x/s for x in w]
    return random.choices([1,2,3,4,5,6], weights=w)[0]

# ==================================================
# TRI & TICKET
# ==================================================
def driver_rank(c):
    return 2 if c.driver_niveau=="FORT" else 0 if c.driver_niveau=="FAIBLE" else 1

def trier_schema(schema):
    return sorted(schema, key=lambda c:(c.score_RSE, driver_rank(c), compter_signaux_ok(c)), reverse=True)

def selection_ticket(schema, face):
    base = schema[0]
    assoc = schema[1:][:max(0,face-1)]
    return [base] + assoc

# ==================================================
# MAIN
# ==================================================
def main():
    fichier = [f for f in os.listdir(".") if f.endswith(".xlsx") and not f.startswith("resultat_")][0]
    print(f"\n📂 Fichier analysé : {fichier}")

    hippo = choisir_hippodrome()
    disc = choisir_discipline()
    regles = DOMAINES[disc]

    df = pd.read_excel(fichier)
    df = df[df["N°"].notna()].copy()

    col_jockey = detecter_colonne(df, ["JOCKEY","JOCKEY/ENTRAINEUR"])
    col_elo_j = detecter_colonne(df, ["ELO JOCKEY","RATING ELO JOCKEY","ELO_JOCKEY"])

    chevaux = []

    for _, r in df.iterrows():
        c = Cheval(r["N°"], r["CHEVAL/MUSIQ."])

        c.set_domaine(
            not (regles["actif_only"] and r.get("Actif") != 1),
            not ((to_float(r.get("Repos")) or 0) > regles["repos_max"])
        )

        c.set_score_rse(calcul_score_rse(r))

        c.set_signaux(
            sigma=(to_float(r.get("SIGMA")) >= SEUILS["SIGMA_MIN"] if r.get("SIGMA") is not None else None),
            ia=(to_float(r.get("PREDICTION IA")) <= SEUILS["IA_RANK_MAX"] if r.get("PREDICTION IA") is not None else None),
            elo=(to_float(r.get("RATING ELO")) >= SEUILS["ELO_MIN"] if r.get("RATING ELO") is not None else None),
            value=(to_float(r.get("COTE")) >= SEUILS["VALUE_COTE_MIN"] if r.get("COTE") is not None else None),
        )

        jockey = extraire_nom_jockey(r.get(col_jockey))
        elo_j = to_float(r.get(col_elo_j))
        c.set_driver(jockey, elo_j)

        chevaux.append(c)

    schema = trier_schema([c for c in chevaux if c.est_dans_domaine()])

    print("\nANALYSE DOMAINE HIPPIQUE – 1RSE")
    print("-"*70)
    for c in schema:
        print(f" - {c.numero} {c.nom} | RSE={c.score_RSE} | JOCKEY={c.driver_nom} ({c.driver_niveau})")

    conf = calcul_confiance(schema)
    face = tirer_face_ponderee(conf, disc)
    if hippo=="vincennes" and disc=="trot" and len(schema)>=6:
        face = max(face,2)

    ticket = selection_ticket(schema, face)
    print("\n🎯 PARI CONSEILLÉ")
    print(f"BASE : {ticket[0].numero} {ticket[0].nom}")
    print(f"TICKET : {[c.numero for c in ticket]}")
    print(f"Confiance : {conf:.2f} | Face : {face}")

if __name__ == "__main__":
    main()
