# rse_checker.py

import csv
from cheval import Cheval
from domaine import appliquer_domaine


def charger_course(fichier):
    chevaux = []

    with open(fichier, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cheval = Cheval(row["numero"], row["nom"])
            cheval = appliquer_domaine(cheval, row)
            chevaux.append(cheval)

    return chevaux


def existe_1RSE(chevaux):
    schema = [c for c in chevaux if c.V and c.F]
    return len(schema) >= 2, schema


def afficher_resultat(chevaux, rse, schema):
    print("\nANALYSE DOMAINE HIPPIQUE")
    print("-" * 30)
    print(f"1RSE : {'OUI' if rse else 'NON'}\n")

    if rse:
        print("Chevaux du schéma (V,F) :")
        for c in schema:
            print(f" - {c.numero} {c.nom}")

    print("\nChevaux hors schéma :")
    for c in chevaux:
        if not (c.V and c.F):
            print(f" - {c.numero} {c.nom} ({int(c.V)},{int(c.F)})")


if __name__ == "__main__":
    chevaux = charger_course("course.csv")
    rse, schema = existe_1RSE(chevaux)
    afficher_resultat(chevaux, rse, schema)
