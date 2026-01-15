# cheval.py
# ==================================================
# OBJET CENTRAL : CHEVAL
# ==================================================

class Cheval:
    """
    Porteur d'information hippique :
    - Domaine : V / F
    - Structure : score_RSE
    - Signaux cheval : SIGMA, IA, ELO, VALUE
    - Jockey : nom + ELO + niveau
    """

    def __init__(self, numero, nom):
        self.numero = int(numero)
        self.nom = str(nom)

        # Domaine
        self.V = True
        self.F = True

        # Structure
        self.score_RSE = 0

        # Signaux cheval
        self.SIGMA_OK = None
        self.IA_OK = None
        self.ELO_OK = None
        self.VALUE_OK = None

        # Jockey / Driver
        self.driver_nom = None
        self.driver_elo = None
        self.driver_niveau = "MOYEN"

    # -----------------
    # Setters
    # -----------------
    def set_domaine(self, V, F):
        self.V = bool(V)
        self.F = bool(F)

    def set_score_rse(self, score):
        self.score_RSE = int(score)

    def set_signaux(self, sigma=None, ia=None, elo=None, value=None):
        self.SIGMA_OK = sigma
        self.IA_OK = ia
        self.ELO_OK = elo
        self.VALUE_OK = value

    def set_driver(self, nom=None, elo=None):
        self.driver_nom = nom
        self.driver_elo = elo

        if elo is None:
            self.driver_niveau = "MOYEN"
        elif elo >= 1600:
            self.driver_niveau = "FORT"
        elif elo >= 1450:
            self.driver_niveau = "MOYEN"
        else:
            self.driver_niveau = "FAIBLE"

    # -----------------
    # Logique
    # -----------------
    def est_dans_domaine(self):
        return self.V and self.F

    def force_structure(self):
        return sum([
            self.SIGMA_OK is True,
            self.IA_OK is True,
            self.ELO_OK is True,
            self.VALUE_OK is True
        ])

    def impact_driver(self):
        if self.driver_elo is None:
            return 0.0
        if self.driver_elo >= 1600:
            return +0.12
        if self.driver_elo >= 1500:
            return +0.05
        if self.driver_elo >= 1450:
            return 0.0
        return -0.10

    # -----------------
    # Représentation
    # -----------------
    def resume(self):
        return (
            f"{self.numero} {self.nom} | "
            f"RSE={self.score_RSE} | "
            f"JOCKEY={self.driver_nom} "
            f"ELO_J={self.driver_elo} ({self.driver_niveau})"
        )

    def to_dict(self):
        return {
            "numero": self.numero,
            "nom": self.nom,
            "V": self.V,
            "F": self.F,
            "score_RSE": self.score_RSE,
            "SIGMA_OK": self.SIGMA_OK,
            "IA_OK": self.IA_OK,
            "ELO_OK": self.ELO_OK,
            "VALUE_OK": self.VALUE_OK,
            "JOCKEY": self.driver_nom,
            "ELO_JOCKEY": self.driver_elo,
            "JOCKEY_NIVEAU": self.driver_niveau
        }
