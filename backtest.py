import pandas as pd
import sys
from collections import defaultdict

# Importer ton système 1RSE
from test_rse_turfbzh import (
    to_float, clamp, calcul_score_rse, compter_signaux_ok,
    calcul_confiance, trier_schema, DOMAINES, SEUILS, BORDAS
)
from cheval import Cheval

def simuler_course(partants_df, hippodrome, discipline):
    """
    Simule l'analyse 1RSE sur une course
    Retourne : base recommandée, ticket, confiance
    """
    regles = DOMAINES.get(discipline)
    if not regles:
        return None, [], 0.0
    
    chevaux = []
    
    for _, row in partants_df.iterrows():
        c = Cheval(row['numero'], row['nom'])
        
        # Domaine
        repos = to_float(row.get('repos'))
        actif = (row.get('actif') == 1)
        
        V = actif if regles["actif_only"] else True
        F = (repos is None) or (repos <= regles["repos_max"])
        
        c.set_domaine(V, F)
        
        # Score RSE (simplifié sans MultiIndex)
        score_rse = 0
        if repos is not None:
            score_rse += 2 if 7 <= repos <= 21 else 1
        if actif:
            score_rse += 1
        # TODO : analyser musique si disponible
        
        c.set_score_rse(score_rse)
        
        # Signaux
        sigma = to_float(row.get('sigma'))
        ia = to_float(row.get('prediction_ia'))
        elo_c = to_float(row.get('elo_cheval'))
        cote = to_float(row.get('cote'))
        
        c.set_signaux(
            sigma=(sigma is not None and sigma >= SEUILS["SIGMA_MIN"]),
            ia=(ia is not None and ia <= SEUILS["IA_RANK_MAX"]),
            elo=(elo_c is not None and elo_c >= SEUILS["ELO_MIN"]),
            value=(cote is not None and cote >= SEUILS["COTE_MIN"])
        )
        
        # Jockey
        elo_j = to_float(row.get('elo_jockey'))
        c.set_driver(row.get('jockey'), elo_j)
        
        chevaux.append(c)
    
    # Tri du schéma
    schema = trier_schema([c for c in chevaux if c.est_dans_domaine()])
    
    if len(schema) < 2:
        return None, [], 0.0
    
    # Confiance
    conf = calcul_confiance(schema, hippodrome)
    
    # Ticket (on prend les 3 premiers pour simplifier)
    ticket = [c.numero for c in schema[:3]]
    base = schema[0].numero
    
    return base, ticket, conf

def evaluer_resultat(base, ticket, arrivee):
    """
    Évalue si la prédiction était bonne
    """
    if not arrivee or len(arrivee) < 3:
        return {'type': 'invalide', 'gagne': False}
    
    top3 = arrivee[:3]
    
    resultats = {
        'base_gagnante': (base == top3[0]),
        'base_placee': (base in top3),
        'couple_gagnant': (len(ticket) >= 2 and ticket[0] == top3[0] and ticket[1] == top3[1]),
        'couple_place': (len(ticket) >= 2 and ticket[0] in top3 and ticket[1] in top3),
        'trio': (len(ticket) >= 3 and all(t in top3 for t in ticket[:3]))
    }
    
    return resultats

def backtest_complet(fichier_excel):
    """
    Lance le backtest sur toutes les courses
    """
    print("🏇 BACKTEST SYSTÈME 1RSE")
    print("=" * 70)
    
    # Charger les données
    df_partants = pd.read_excel(fichier_excel, sheet_name='Partants')
    df_courses = pd.read_excel(fichier_excel, sheet_name='Courses')
    
    print(f"📊 {len(df_courses)} courses à analyser")
    
    stats_globales = {
        'total_courses': 0,
        'courses_jouables': 0,
        'base_gagnante': 0,
        'base_placee': 0,
        'couple_gagnant': 0,
        'couple_place': 0,
        'trio': 0
    }
    
    stats_par_hippo = defaultdict(lambda: stats_globales.copy())
    stats_par_discipline = defaultdict(lambda: stats_globales.copy())
    
    resultats_detailles = []
    
    for _, course in df_courses.iterrows():
        stats_globales['total_courses'] += 1
        
        # Filtrer les partants de cette course
        mask = (
            (df_partants['date'] == course['date']) &
            (df_partants['hippodrome'] == course['hippodrome']) &
            (df_partants['numero_course'] == course['numero_course'])
        )
        partants = df_partants[mask]
        
        if len(partants) == 0:
            continue
        
        # Simuler l'analyse
        base, ticket, conf = simuler_course(
            partants,
            course['hippodrome'],
            course['discipline']
        )
        
        if base is None:
            continue
        
        stats_globales['courses_jouables'] += 1
        
        # Récupérer l'arrivée
        arrivee = [
            course['arrivee_1'],
            course['arrivee_2'],
            course['arrivee_3']
        ]
        arrivee = [int(a) for a in arrivee if pd.notna(a)]
        
        # Évaluer
        resultats = evaluer_resultat(base, ticket, arrivee)
        
        if resultats['base_gagnante']:
            stats_globales['base_gagnante'] += 1
        if resultats['base_placee']:
            stats_globales['base_placee'] += 1
        if resultats.get('couple_gagnant'):
            stats_globales['couple_gagnant'] += 1
        if resultats.get('couple_place'):
            stats_globales['couple_place'] += 1
        if resultats.get('trio'):
            stats_globales['trio'] += 1
        
        # Stocker résultat détaillé
        resultats_detailles.append({
            'date': course['date'],
            'hippodrome': course['hippodrome'],
            'course': course['numero_course'],
            'discipline': course['discipline'],
            'base': base,
            'ticket': ticket,
            'confiance': conf,
            'arrivee': arrivee,
            **resultats
        })
    
    # Afficher les résultats
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS BACKTEST")
    print("=" * 70)
    
    if stats_globales['courses_jouables'] > 0:
        print(f"\n🎯 STATISTIQUES GLOBALES")
        print(f"   Courses analysées : {stats_globales['total_courses']}")
        print(f"   Courses jouables : {stats_globales['courses_jouables']}")
        print(f"   Taux de sélection : {stats_globales['courses_jouables']/stats_globales['total_courses']*100:.1f}%")
        print()
        print(f"   Base gagnante : {stats_globales['base_gagnante']} ({stats_globales['base_gagnante']/stats_globales['courses_jouables']*100:.1f}%)")
        print(f"   Base placée : {stats_globales['base_placee']} ({stats_globales['base_placee']/stats_globales['courses_jouables']*100:.1f}%)")
        print(f"   Couplé gagnant : {stats_globales['couple_gagnant']} ({stats_globales['couple_gagnant']/stats_globales['courses_jouables']*100:.1f}%)")
        print(f"   Couplé placé : {stats_globales['couple_place']} ({stats_globales['couple_place']/stats_globales['courses_jouables']*100:.1f}%)")
        print(f"   Trio : {stats_globales['trio']} ({stats_globales['trio']/stats_globales['courses_jouables']*100:.1f}%)")
    
    # Sauvegarder les résultats détaillés
    df_resultats = pd.DataFrame(resultats_detailles)
    fichier_sortie = "backtest_resultats.xlsx"
    df_resultats.to_excel(fichier_sortie, index=False)
    print(f"\n💾 Résultats détaillés sauvegardés : {fichier_sortie}")
    
    return stats_globales

def main():
    fichier = input("📂 Fichier Excel consolidé (ex: backtest_2025_consolide.xlsx) : ").strip()
    
    if not fichier.endswith('.xlsx'):
        fichier += '.xlsx'
    
    try:
        backtest_complet(fichier)
    except FileNotFoundError:
        print(f"❌ Fichier {fichier} introuvable !")
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()