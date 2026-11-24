# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Rapport « à mettre à jour à la main » — v1.0 (24/11/2026)
#  Lancé chaque nuit après les autres scripts :
#   1. rassemble rapport/*.json dans data/a_mettre_a_jour.json (lu par le
#      récapitulatif mensuel des élections, envoyé le 1er du mois) ;
#   2. ouvre un ticket GitHub pour chaque chambre toujours pas mise à jour
#      21 jours après son élection — GitHub prévient Maximilien par e-mail.
#      Un seul ticket par chambre et par élection (pas de doublon).
# ══════════════════════════════════════════════════════════════════
import json, os, glob, requests
from datetime import datetime

ICI = os.path.dirname(os.path.abspath(__file__))
TITRES = {"chambres": "Chambres renouvelées pas encore mises à jour",
          "elections_sans_resultat": "Élections nationales passées sans résultat",
          "dirigeants_nationaux": "Dirigeants nationaux : désaccords entre sources",
          "dirigeants_regionaux": "Dirigeants régionaux : changements confirmés mais non appliqués"}

def main():
    rapport = {"genere_le": datetime.now().strftime("%Y-%m-%d %H:%M")}
    for f in glob.glob(os.path.join(ICI, "rapport", "*.json")):
        try: rapport[os.path.basename(f)[:-5]] = json.load(open(f, encoding="utf-8"))
        except Exception: pass
    sortie = os.path.join(ICI, "data", "a_mettre_a_jour.json")
    ancien = {}
    try: ancien = json.load(open(sortie, encoding="utf-8"))
    except Exception: pass
    for k in TITRES:                          # section absente cette nuit (script en panne) : on garde la précédente
        if k not in rapport and k in ancien: rapport[k] = ancien[k]
    json.dump(rapport, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, t in TITRES.items(): print(f"  {t} : {len(rapport.get(k, []))}")

    # Tickets GitHub (e-mail) : chambres en attente depuis 21 jours ou plus
    jeton, depot = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (jeton and depot): print("  (pas de jeton GitHub : aucun ticket)"); return
    h = {"Authorization": f"Bearer {jeton}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{depot}/issues"
    try:
        existants = {i["title"] for i in requests.get(api, headers=h, params={"state": "all", "labels": "a-mettre-a-jour", "per_page": 100}, timeout=30).json()}
    except Exception as e:
        print(f"  ✗ tickets illisibles : {e}"); return
    for c in rapport.get("chambres", []):
        if c.get("jours", 0) < 21: continue
        titre = f"À mettre à jour : {c['pays']} — {c['chambre']} (élection du {c['election']})"
        if titre in existants: continue
        corps = (f"La chambre **{c['chambre']}** ({c['pays']}) a été renouvelée lors de l'élection du {c['election']}, "
                 f"il y a {c['jours']} jours, mais aucune source n'a permis de mettre à jour la répartition des sièges automatiquement.\n\n"
                 "Le site affiche « renouvellement en cours ». À faire : saisir la nouvelle répartition dans la version de test "
                 "(CHAMBRES_COMPOSITION), puis relancer l'export (`node tools/export_regions_chambres.js`).\n\n"
                 "Ticket ouvert automatiquement par l'automatisation de nuit de Geolandar.")
        r = requests.post(api, headers=h, json={"title": titre, "body": corps, "labels": ["a-mettre-a-jour"]}, timeout=30)
        print(f"  {'✓' if r.ok else '✗'} ticket : {titre}")

if __name__ == "__main__":
    main()
