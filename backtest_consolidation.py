import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

def lire_triplet_course(dossier, date, reunion, course):
    """
    Lit les 3 fichiers JSON d'une course :
    - infos.json : données générales
    - partants.json : liste des chevaux
    - rapports.json : résultats / arrivée
    """
    base_name = f"{date}_{reunion}_C{course}"
    
    fichier_infos = dossier / date / f"{base_name}_infos.json"
    fichier_partants = dossier / date / f"{base_name}_partants.json"
    fichier_rapports = dossier / date / f"{base_name}_rapp_orts.json"
    
    # Charger infos
    infos = {}
    if fichier_infos.exists():
        with open(fichier_infos, 'r', encoding='utf-8') as f:
            infos = json.load(f)
    
    # Charger partants
    partants = []
    if fichier_partants.exists():
        with open(fichier_partants, 'r', encoding='utf-8') as f:
            partants = json.load(f)
    
    # Charger rapports/arrivée
    rapports = {}
    arrivee = []
    if fichier_rapports.exists():
        with open(fichier_rapports, 'r', encoding='utf-8') as f:
            rapports = json.load(f)
            # L'arrivée peut être dans différents champs selon le format
            arrivee = rapports.get('arrivee', rapports.get('ordre_arrivee', []))
    
    return infos, partants, arrivee

def extraire_tous_les_triplets(dossier_racine):
    """
    Parcourt le dossier dataRaceJson et extrait tous les triplets de courses
    Format: 2025-01-10_R4_C6_participants.json (tous dans le même dossier)
    """
    dossier = Path(dossier_racine)
    
    if not dossier.exists():
        print(f"❌ Le dossier {dossier} n'existe pas !")
        return []
    
    print(f"📂 Analyse du dossier : {dossier}")
    
    # Lister tous les fichiers _participants.json
    fichiers_participants = list(dossier.glob("*_participants.json"))
    
    print(f"🐎 {len(fichiers_participants)} fichiers partants trouvés")
    
    courses_extraites = []
    
    for fichier in fichiers_participants:
        # Format: 2025-01-10_R4_C6_participants.json
        # On extrait: date, reunion, course
        parts = fichier.stem.replace('_participants', '').split('_')
        
        if len(parts) >= 3:
            date = parts[0]  # 2025-01-10
            reunion = parts[1]  # R4
            course = parts[2].replace('C', '')  # C6 -> 6
            
            # Construire les noms des 3 fichiers
            base_name = f"{date}_{reunion}_C{course}"
            fichier_infos = dossier / f"{base_name}_infos.json"
            fichier_partants = fichier
            fichier_rapports = dossier / f"{base_name}_rapports.json"
            
            try:
                # Charger infos
                infos = {}
                if fichier_infos.exists():
                    with open(fichier_infos, 'r', encoding='utf-8') as f:
                        infos = json.load(f)
                
                # Charger partants
                partants = []
                with open(fichier_partants, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Le JSON contient "participants" comme clé racine
                    partants = data.get('participants', data if isinstance(data, list) else [])
                
                # Charger rapports/arrivée
                rapports = {}
                arrivee = []
                if fichier_rapports.exists():
                    with open(fichier_rapports, 'r', encoding='utf-8') as f:
                        rapports = json.load(f)
                
                # Extraire l'ordre d'arrivée depuis infos.json
                ordre_arrivee = infos.get('ordreArrivee', [])
                if ordre_arrivee:
                    arrivee = ordre_arrivee
                
                if partants:  # Seulement si on a des partants
                    courses_extraites.append({
                        'date': date,
                        'reunion': reunion,
                        'course': course,
                        'infos': infos,
                        'partants': partants,
                        'arrivee': arrivee
                    })
                    
            except Exception as e:
                print(f"⚠️ Erreur sur {fichier.name}: {e}")
    
    return courses_extraites

def creer_excel_backtest(dossier_json, fichier_sortie="backtest_2025.xlsx"):
    """
    Crée un fichier Excel prêt pour le backtest
    """
    print("🏇 CONSOLIDATION DES COURSES POUR BACKTEST")
    print("=" * 70)
    
    courses = extraire_tous_les_triplets(dossier_json)
    
    if not courses:
        print("❌ Aucune course trouvée !")
        return
    
    print(f"\n✅ {len(courses)} courses extraites")
    
    # Construire les DataFrames
    toutes_lignes_partants = []
    toutes_lignes_courses = []
    
    for course in courses:
        date = course['date']
        reunion = course['reunion']
        num_course = course['course']
        infos = course['infos']
        partants = course['partants']
        arrivee = course['arrivee']
        
        # Infos de la course
        hippodrome = infos.get('hippodrome', {}).get('libelleCourt', 'inconnu')
        discipline = infos.get('discipline', 'inconnu')
        distance = infos.get('distance', None)
        
        # Ligne pour l'onglet Courses
        toutes_lignes_courses.append({
            'date': date,
            'reunion': reunion,
            'course': num_course,
            'hippodrome': hippodrome,
            'discipline': discipline,
            'distance': distance,
            'nb_partants': len(partants),
            'arrivee_1': arrivee[0] if len(arrivee) > 0 else None,
            'arrivee_2': arrivee[1] if len(arrivee) > 1 else None,
            'arrivee_3': arrivee[2] if len(arrivee) > 2 else None,
        })
        
        # Lignes pour l'onglet Partants
        for p in partants:
            # Extraire les données selon le format de ton JSON
            toutes_lignes_partants.append({
                'date': date,
                'reunion': reunion,
                'course': num_course,
                'hippodrome': hippodrome,
                'discipline': discipline,
                'numero': p.get('numPmu', p.get('numero', None)),
                'nom': p.get('nom', ''),
                'jockey': p.get('driver', p.get('jockey', '')),
                'cote': p.get('dernierRapportReference', {}).get('rapport', None),
                'elo_cheval': None,  # À ajouter si disponible
                'elo_jockey': None,  # À ajouter si disponible
                'repos': None,  # À ajouter si disponible
                'actif': None,  # À ajouter si disponible
                'sigma': None,  # À ajouter si disponible
                'prediction_ia': None,  # À ajouter si disponible
                'musique': '',  # À ajouter si disponible
                'ordre_arrivee': p.get('ordreArrivee', None),
            })
    
    # Créer les DataFrames
    df_partants = pd.DataFrame(toutes_lignes_partants)
    df_courses = pd.DataFrame(toutes_lignes_courses)
    
    # Sauvegarder
    with pd.ExcelWriter(fichier_sortie, engine='openpyxl') as writer:
        df_partants.to_excel(writer, sheet_name='Partants', index=False)
        df_courses.to_excel(writer, sheet_name='Courses', index=False)
    
    print(f"\n✅ Fichier Excel créé : {fichier_sortie}")
    print(f"📊 {len(df_courses)} courses")
    print(f"🐎 {len(df_partants)} partants")
    
    # Statistiques par hippodrome
    print("\n📍 Répartition par hippodrome :")
    for hippo, count in df_courses['hippodrome'].value_counts().head(10).items():
        print(f"   {hippo}: {count} courses")
    
    # Statistiques par discipline
    print("\n🏇 Répartition par discipline :")
    for disc, count in df_courses['discipline'].value_counts().items():
        print(f"   {disc}: {count} courses")
    
    return fichier_sortie

def main():
    # Chemin par défaut
    chemin_defaut = "../dataRaceJson"
    
    print("🏇 CONSOLIDATION JSON → EXCEL POUR BACKTEST")
    print("=" * 70)
    
    chemin = input(f"\n📂 Chemin du dossier dataRaceJson (défaut: {chemin_defaut}) : ").strip()
    
    if not chemin:
        chemin = chemin_defaut
    
    # Expansion du ~ si présent
    chemin = os.path.expanduser(chemin)
    
    if not os.path.exists(chemin):
        print(f"❌ Le dossier {chemin} n'existe pas !")
        print(f"📂 Dossier actuel : {os.getcwd()}")
        print(f"💡 Essaie avec le chemin absolu complet")
        return
    
    # Debug : afficher ce qui est trouvé
    print(f"✅ Dossier trouvé : {os.path.abspath(chemin)}")
    print(f"📁 Contenu :")
    items = list(Path(chemin).iterdir())[:10]  # Premiers 10 items
    for item in items:
        print(f"   - {item.name}")
    
    # Créer le fichier Excel
    creer_excel_backtest(chemin)
    
    print("\n🎯 PROCHAINE ÉTAPE : Lance 'python backtest_analyse.py' !")

if __name__ == "__main__":
    main()