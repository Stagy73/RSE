import pandas as pd
import sys
from collections import defaultdict

def analyser_favoris(fichier_excel):
    """
    Analyse basique : performance des favoris (cote la plus basse)
    """
    print("🏇 BACKTEST SIMPLIFIÉ - ANALYSE DES FAVORIS")
    print("=" * 70)
    
    # Charger les données
    try:
        df_partants = pd.read_excel(fichier_excel, sheet_name='Partants')
        df_courses = pd.read_excel(fichier_excel, sheet_name='Courses')
    except Exception as e:
        print(f"❌ Erreur lecture fichier : {e}")
        return
    
    print(f"📊 {len(df_courses)} courses à analyser")
    print(f"🐎 {len(df_partants)} partants au total")
    
    stats = {
        'total_courses': 0,
        'courses_analysables': 0,
        'favori_gagnant': 0,
        'favori_place': 0,
        'top3_gagnant': 0,
    }
    
    for _, course in df_courses.iterrows():
        stats['total_courses'] += 1
        
        # Filtrer les partants de cette course
        mask = (
            (df_partants['date'] == course['date']) &
            (df_partants['reunion'] == course['reunion']) &
            (df_partants['course'] == course['course'])
        )
        partants = df_partants[mask].copy()
        
        if len(partants) == 0:
            continue
        
        # Vérifier qu'on a une arrivée
        arrivee = []
        for a in [course['arrivee_1'], course['arrivee_2'], course['arrivee_3']]:
            if pd.notna(a):
                try:
                    arrivee.append(int(a))
                except (ValueError, TypeError):
                    pass
        
        if len(arrivee) == 0:
            continue
        
        # Vérifier qu'on a des cotes
        partants_avec_cote = partants[partants['cote'].notna()]
        if len(partants_avec_cote) == 0:
            continue
        
        stats['courses_analysables'] += 1
        
        # Trouver le favori (cote la plus basse)
        favori = partants_avec_cote.loc[partants_avec_cote['cote'].idxmin()]
        num_favori = favori['numero']
        
        # Trouver les 3 plus petites cotes
        top3_cotes = partants_avec_cote.nsmallest(3, 'cote')
        nums_top3 = top3_cotes['numero'].tolist()
        
        # Évaluer
        if num_favori == arrivee[0]:
            stats['favori_gagnant'] += 1
        
        if num_favori in arrivee[:3]:
            stats['favori_place'] += 1
        
        if arrivee[0] in nums_top3:
            stats['top3_gagnant'] += 1
    
    # Afficher résultats
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS BACKTEST")
    print("=" * 70)
    
    if stats['courses_analysables'] > 0:
        print(f"\n🎯 STATISTIQUES GLOBALES")
        print(f"   Courses totales : {stats['total_courses']}")
        print(f"   Courses analysables : {stats['courses_analysables']}")
        print(f"   Taux analysable : {stats['courses_analysables']/stats['total_courses']*100:.1f}%")
        print()
        print(f"   Favori gagnant : {stats['favori_gagnant']} ({stats['favori_gagnant']/stats['courses_analysables']*100:.1f}%)")
        print(f"   Favori placé : {stats['favori_place']} ({stats['favori_place']/stats['courses_analysables']*100:.1f}%)")
        print(f"   Top 3 cotes gagnant : {stats['top3_gagnant']} ({stats['top3_gagnant']/stats['courses_analysables']*100:.1f}%)")
    else:
        print("❌ Aucune course analysable trouvée !")
    
    return stats

def analyser_par_hippodrome(fichier_excel):
    """
    Analyse par hippodrome
    """
    print("\n" + "=" * 70)
    print("📍 ANALYSE PAR HIPPODROME")
    print("=" * 70)
    
    try:
        df_partants = pd.read_excel(fichier_excel, sheet_name='Partants')
        df_courses = pd.read_excel(fichier_excel, sheet_name='Courses')
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return
    
    # Compter par hippodrome
    hippo_counts = df_courses['hippodrome'].value_counts().head(10)
    
    print("\n🏟️ Top 10 hippodromes (nombre de courses) :")
    for hippo, count in hippo_counts.items():
        print(f"   {hippo:20s} : {count:4d} courses")
    
    # Statistiques par discipline
    print("\n🏇 Répartition par discipline :")
    disc_counts = df_courses['discipline'].value_counts()
    for disc, count in disc_counts.items():
        print(f"   {disc:20s} : {count:4d} courses")

def main():
    print("🏇 BACKTEST SYSTÈME 1RSE")
    print("=" * 70)
    
    fichier = input("\n📂 Fichier Excel consolidé (défaut: backtest_2025.xlsx) : ").strip()
    
    if not fichier:
        fichier = "backtest_2025.xlsx"
    
    if not fichier.endswith('.xlsx'):
        fichier += '.xlsx'
    
    try:
        analyser_favoris(fichier)
        analyser_par_hippodrome(fichier)
        
        print("\n" + "=" * 70)
        print("✅ Analyse terminée !")
        print("=" * 70)
        
    except FileNotFoundError:
        print(f"❌ Fichier {fichier} introuvable !")
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()