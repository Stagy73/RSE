import pandas as pd

def exporter_excel(df, fichier="resultat_rse.xlsx"):
    df.to_excel(fichier, index=False)
