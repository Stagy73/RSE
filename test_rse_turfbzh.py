import pandas as pd
import os
import sys
import random
import hashlib
from collections import Counter

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
    except Exception:
        return None

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

# ==================================================
# NORMALISATION COLONNES EXCEL (MultiIndex)
# ==================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            " | ".join(
                str(x).strip()
                for x in col
                if str(x).strip() not in ["", "nan", "None"]
            )
            for col in df.columns
        ]
    else:
        df.columns = [str(c).strip() for c in df.columns]
    return df

# ==================================================
# DÉTECTION COLONNE EXACTE / INCLUSION
# ==================================================
def detecter_colonne(df, noms, exclure_patterns=None):
    """
    Détecte une colonne par nom exact ou inclusion.
    exclure_patterns: liste de patterns à exclure (ex: ["RATING ELO", "ELO"])
    """
    cols = list(df.columns)
    cols_low = {str(c).lower(): c for c in cols}

    # Filtre d'exclusion
    if exclure_patterns:
        cols_filtrees = []
        for c in cols:
            c_low = str(c).lower()
            if not any(pattern.lower() in c_low for pattern in exclure_patterns):
                cols_filtrees.append(c)
        cols = cols_filtrees
        cols_low = {str(c).lower(): c for c in cols}

    # exact (prioritaire)
    for n in noms:
        if n in cols:
            return n

    # inclusion
    for n in noms:
        n_low = n.lower()
        for c_low, c in cols_low.items():
            if n_low in c_low:
                return c

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

def require_col(colname, label):
    if not colname:
        print(f"❌ Colonne obligatoire introuvable : {label}")
        sys.exit(1)

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
    print("\n🏟️ Choisis l'hippodrome :")
    for k, v in HIPPODROMES.items():
        print(f"{k} - {v if v else 'aucun'}")
    choix = input("👉 Ton choix : ").strip()
    return HIPPODROMES.get(choix)

def choisir_discipline():
    print("\n🏇 Choisis la discipline :")
    for k, v in DISCIPLINES.items():
        print(f"{k} - {v}")
    choix = input("👉 Ton choix : ").strip()
    return DISCIPLINES.get(choix)

# ==================================================
# DOMAINES MÉTIER (SANS COTE)
# ==================================================
DOMAINES = {
    "trot":     {"repos_max": 30, "actif_only": True},
    "monte":    {"repos_max": 21, "actif_only": True},
    "plat":     {"repos_max": 25, "actif_only": True},
    "obstacle": {"repos_max": 60, "actif_only": False},
}

SEUILS = {
    "SIGMA_MIN": 55.0,
    "IA_RANK_MAX": 5.0,
    "ELO_MIN": 1400.0
}

# ==================================================
# SCORE RSE (SANS COTE)
# ==================================================
def calcul_score_rse(row, df_columns):
    """
    Calcule le score RSE en cherchant les colonnes même avec MultiIndex
    """
    score = 0
    
    # Chercher la colonne Repos
    repos = None
    for col in df_columns:
        if "repos" in str(col).lower():
            repos = to_float(row.get(col))
            break
    
    if repos is not None:
        score += 2 if 7 <= repos <= 21 else 1
    
    # Chercher la colonne Actif
    actif = False
    for col in df_columns:
        if "actif" in str(col).lower():
            actif = (row.get(col) == 1)
            break
    
    if actif:
        score += 1

    return score

# ==================================================
# CONFIANCE
# ==================================================
def compter_signaux_ok(c: Cheval):
    return sum([
        c.SIGMA_OK is True,
        c.IA_OK is True,
        c.ELO_OK is True
    ])

def calcul_confiance(schema):
    if len(schema) < 2:
        return 0.0

    base, second = schema[0], schema[1]
    gap = clamp((base.score_RSE - second.score_RSE) / 3)
    sig = compter_signaux_ok(base) / 3
    size = clamp(1 - (len(schema) - 2) / 8)

    conf = 0.45 * gap + 0.35 * sig + 0.20 * size
    conf += base.impact_driver()   # ELO jockey via cheval.py

    return clamp(conf)

# ==================================================
# RNG DÉTERMINISTE
# ==================================================
def stable_seed(fichier, hippo, disc, schema):
    key = (
        os.path.basename(fichier)
        + "|"
        + str(hippo)
        + "|"
        + str(disc)
        + "|"
        + ",".join(str(c.numero) for c in schema)
    )
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)

# ==================================================
# TIRAGE DÉ PONDÉRÉ (DÉTERMINISTE)
# ==================================================
def tirer_face(conf, disc, rng):
    if conf >= 0.75:
        w = [0.35, 0.30, 0.20, 0.10, 0.04, 0.01]
    elif conf >= 0.5:
        w = [0.20, 0.28, 0.24, 0.18, 0.07, 0.03]
    else:
        w = [0.06, 0.12, 0.22, 0.25, 0.22, 0.13]

    if disc == "obstacle":
        w = [x * 0.25 for x in w]
        w[2] *= 1.2
        w[3] *= 1.5
        w[4] *= 1.8
        w[5] *= 2.2

    s = sum(w)
    w = [x / s for x in w]
    return rng.choices([1, 2, 3, 4, 5, 6], weights=w)[0]

# ==================================================
# TRI & TICKET
# ==================================================
def driver_rank(c):
    if c.driver_niveau == "FORT":
        return 2
    if c.driver_niveau == "FAIBLE":
        return 0
    return 1

def trier_schema(schema):
    return sorted(
        schema,
        key=lambda c: (c.score_RSE, driver_rank(c), compter_signaux_ok(c)),
        reverse=True
    )

def selection_ticket(schema, face):
    face = max(1, min(int(face), len(schema)))
    return schema[:face]

def face_to_pari(face, conf):
    if face == 1:
        return "Simple Gagnant" if conf >= 0.70 else "Simple Placé"
    if face == 2:
        return "Couplé Gagnant" if conf >= 0.60 else "Couplé Placé"
    if face == 3:
        return "Trio"
    if face == 4:
        return "Multi 4"
    if face == 5:
        return "Multi 5"
    return "Multi 6"

# ==================================================
# SÉLECTION FICHIER (AUTO si 1)
# ==================================================
def choisir_fichier_xlsx():
    fichiers = [f for f in os.listdir(".") if f.endswith(".xlsx") and not f.startswith("resultat_")]
    if not fichiers:
        print("❌ Aucun fichier Excel (.xlsx) trouvé dans le dossier.")
        sys.exit(1)

    if len(fichiers) == 1:
        fichier = fichiers[0]
        print(f"📂 Fichier détecté automatiquement : {fichier}")
        return fichier

    # Sinon: proposer liste
    print("\n📂 Fichiers disponibles :")
    for i, f in enumerate(fichiers, 1):
        print(f"{i} - {f}")

    choix = input("\n👉 Choisis le fichier (numéro OU nom exact) : ").strip()

    # choix par numéro
    if choix.isdigit():
        idx = int(choix) - 1
        if 0 <= idx < len(fichiers):
            return fichiers[idx]
        print("❌ Numéro invalide.")
        sys.exit(1)

    # choix par nom
    if choix in fichiers:
        return choix

    print("❌ Choix invalide (ni numéro, ni nom exact).")
    sys.exit(1)

# ==================================================
# MAIN
# ==================================================
def main():
    fichier = choisir_fichier_xlsx()
    print(f"\n📂 Fichier : {fichier}")

    hippo = choisir_hippodrome()
    disc = choisir_discipline()
    if disc not in DOMAINES:
        print("❌ Discipline invalide.")
        sys.exit(1)
    regles = DOMAINES[disc]

    # Lire avec les 2 lignes d'en-têtes (MultiIndex)
    df = pd.read_excel(fichier, header=[0, 1])
    df = normalize_columns(df)

    # Colonnes principales (EXCLURE les colonnes ELO de la recherche JOCKEY)
    col_num = detecter_colonne(df, ["N°", "Nº", "NUM", "NO"])
    col_nom = detecter_colonne(df, ["CHEVAL/MUSIQ.", "CHEVAL", "CHEVAL | MUSIQ", "CHEVAL/MUSIQUE"])
    col_jockey = detecter_colonne(df, ["JOCKEY", "DRIVER", "DRIVER/JOCKEY", "JOCKEY/ENTRAINEUR", "DRIVER/ENTRAINEUR"], 
                                   exclure_patterns=["RATING ELO", "ELO"])

    require_col(col_num, "N° / NUM")
    require_col(col_nom, "CHEVAL")

    # ⭐ ELO : Détection avec les noms MultiIndex normalisés
    col_elo_cheval = detecter_colonne(df, ["RATING ELO | CHEVAL", "RATING ELO CHEVAL", "ELO CHEVAL", "RATING ELO"])
    
    # Pour le jockey : cherche dans toutes les colonnes qui contiennent "JOCKEY" et "ELO"
    col_elo_jockey = None
    for col in df.columns:
        col_low = str(col).lower()
        if "jockey" in col_low and ("elo" in col_low or "rating" in col_low):
            col_elo_jockey = col
            break

    print(f"🧑‍✈️ Colonne JOCKEY : {col_jockey}")
    print(f"🐎 Colonne ELO CHEVAL : {col_elo_cheval}")
    print(f"📈 Colonne ELO JOCKEY : {col_elo_jockey}")

    chevaux = []

    for _, r in df.iterrows():
        if pd.isna(r.get(col_num)):
            continue

        c = Cheval(r.get(col_num), str(r.get(col_nom)).strip())

        # 🔍 DEBUG : vérifier les colonnes critiques
        repos = to_float(r.get("Repos"))
        actif = (r.get("Actif") == 1)
        
        # Chercher aussi avec le suffixe MultiIndex
        if repos is None:
            for col in df.columns:
                if "repos" in str(col).lower():
                    repos = to_float(r.get(col))
                    break
        
        if not actif:
            for col in df.columns:
                if "actif" in str(col).lower():
                    actif = (r.get(col) == 1)
                    break

        V = actif if regles["actif_only"] else True
        F = (repos is None) or (repos <= regles["repos_max"])

        c.set_domaine(V, F)
        c.set_score_rse(calcul_score_rse(r, df.columns))

        # Chercher SIGMA et IA avec le suffixe MultiIndex
        sigma = to_float(r.get("SIGMA"))
        if sigma is None:
            for col in df.columns:
                if "sigma" in str(col).lower() and "rating elo" not in str(col).lower():
                    sigma = to_float(r.get(col))
                    break
        
        ia = to_float(r.get("PREDICTION IA"))
        if ia is None:
            for col in df.columns:
                col_str = str(col).lower()
                if "prediction" in col_str and "ia" in col_str and "gagnant" in col_str:
                    ia = to_float(r.get(col))
                    break

        # Lecture ELO avec gestion robuste
        elo_c = None
        if col_elo_cheval and col_elo_cheval in r.index:
            elo_c = to_float(r.get(col_elo_cheval))
        
        elo_j = None
        if col_elo_jockey and col_elo_jockey in r.index:
            elo_j = to_float(r.get(col_elo_jockey))

        c.set_signaux(
            sigma=(sigma is not None and sigma >= SEUILS["SIGMA_MIN"]),
            ia=(ia is not None and ia <= SEUILS["IA_RANK_MAX"]),
            elo=(elo_c is not None and elo_c >= SEUILS["ELO_MIN"]),
            value=None  # SANS COTE
        )

        jockey = extraire_nom_jockey(r.get(col_jockey)) if col_jockey else None
        c.set_driver(jockey, elo_j)

        chevaux.append(c)

    schema = trier_schema([c for c in chevaux if c.est_dans_domaine()])

    print("\nANALYSE DOMAINE HIPPIQUE – 1RSE (SANS COTE)")
    print("-" * 70)

    if len(schema) < 2:
        print("❌ 1RSE : NO BET (pas assez de chevaux dans le domaine)")
        sys.exit(0)

    for c in schema:
        print(
            f" - {c.numero} {c.nom} | RSE={c.score_RSE} | "
            f"OK={compter_signaux_ok(c)}/3 | "
            f"JOCKEY={c.driver_nom} ELO_J={c.driver_elo} ({c.driver_niveau})"
        )

    conf = calcul_confiance(schema)
    seed = stable_seed(fichier, hippo, disc, schema)
    rng = random.Random(seed)

    tirages = [tirer_face(conf, disc, rng) for _ in range(5)]
    face_finale = Counter(tirages).most_common(1)[0][0]

    ticket = selection_ticket(schema, face_finale)

    print("\n🎲 SIMULATION 5 TIRAGES (DÉTERMINISTE)")
    print("-" * 70)
    print(tirages)

    print("\n🎯 VERDICT FINAL")
    print("-" * 70)
    print(f"🥇 BASE : {ticket[0].numero} {ticket[0].nom}")
    print(f"🎟️ Ticket : {[c.numero for c in ticket]}")
    print(f"✅ Pari : {face_to_pari(face_finale, conf)}")
    print(f"📊 Confiance : {conf:.2f} | Face finale : {face_finale}")
    print(f"🔒 Seed : {seed} (mêmes données => mêmes résultats)")

if __name__ == "__main__":
    main()