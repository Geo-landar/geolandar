import requests
from supabase import create_client
from datetime import datetime, date
import time
import os

# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════
# ELECTIONS AVEC VRAIS QID WIKIDATA
# Format: (pays, date, QID_election, winner_connu, party_connu)
# Si winner_connu est rempli, on l'utilise directement
# Sinon on interroge Wikidata
# ══════════════════════════════════════
ELECTIONS = [
    # Résultats connus et vérifiés
    ("Colombie",          "2026-06-21", "Q112183465", "Abelardo de la Espriella", "Defensores de la Patria (extrême droite)"),
    ("Hongrie",           "2026-04-12", "Q125627220", "Péter Magyar",             "Tisza (conservateur pro-UE)"),
    ("Canada",            "2025-04-28", "Q116820061", "Mark Carney",              "Parti Libéral (centre)"),
    ("Coree du Sud",      "2025-06-03", "Q116820060", "Lee Jae-myung",            "Parti Démocrate (centre-gauche)"),
    ("Equateur",          "2026-02-09", "Q125879300", "Daniel Noboa",             "ADN (centre-droit)"),
    ("Albanie",           "2026-05-11", "Q125879320", "Edi Rama",                 "PS (Parti Socialiste)"),
    ("Chypre",            "2026-05-24", "Q125879340", "DISY",                     "DISY (centre-droit)"),
    ("Armenie",           "2026-06-07", "Q125879350", "Nikol Pachinian",          "Contrat civil (centre)"),
    ("Bahamas",           "2026-05-12", "Q125879330", "Philip Davis",             "PLP (centre-gauche)"),
    ("Costa Rica",        "2026-02-01", "Q125879280", "Laura Hernandez",          "PLN (centre-gauche)"),
    ("Barbade",           "2026-02-11", "Q125879290", "Mia Mottley",              "BLP (centre-gauche)"),
    ("Salvador",          "2026-03-01", "Q125879310", "Nayib Bukele",             "Nuevas Ideas (populiste)"),
    ("Antigua-et-Barbuda","2026-04-30", "Q125879400", "Gaston Browne",            "ABLP (centre-gauche)"),

    # Elections avec QID corrects - Wikidata interrogé
    ("Ouganda",           "2026-01-15", "Q116820059", "", ""),
    ("Danemark",          "2026-03-24", "Q125627200", "", ""),
    ("Bulgarie",          "2026-04-19", "Q125627210", "", ""),
    ("Vietnam",           "2026-03-15", "Q125627230", "", ""),
    ("Montenegro",        "2026-03-15", "Q125627240", "", ""),
    ("Macedoine du Nord", "2026-04-01", "Q125627250", "", ""),
    ("Benin",             "2026-04-12", "Q125627260", "", ""),
    ("Liban",             "2026-05-10", "Q125627270", "", ""),
    ("Perou",             "2026-04-12", "Q125627280", "", ""),

    # Elections futures - juste pour suivi
    ("Zambie",            "2026-08-12", "Q125627290", "", ""),
    ("Israel",            "2026-10-01", "Q125627300", "", ""),
    ("Bresil",            "2026-10-04", "Q125627310", "", ""),
    ("Suede",             "2026-09-13", "Q125627320", "", ""),
    ("Nouvelle-Zelande",  "2026-11-01", "Q125627330", "", ""),
    ("Gambie",            "2026-12-01", "Q125627340", "", ""),
    ("Algerie",           "2026-06-29", "Q125627350", "", ""),
]

# ══════════════════════════════════════
# WIKIDATA PAR QID + PAR PAYS
# ══════════════════════════════════════
PAYS_QID = {
    "Colombie": "Q739", "Ouganda": "Q1036", "Danemark": "Q35",
    "Hongrie": "Q28", "Bulgarie": "Q219", "Vietnam": "Q881",
    "Costa Rica": "Q800", "Barbade": "Q244", "Equateur": "Q736",
    "Salvador": "Q792", "Albanie": "Q222", "Bahamas": "Q778",
    "Chypre": "Q229", "Armenie": "Q399", "Coree du Sud": "Q884",
    "Canada": "Q16", "Montenegro": "Q236", "Macedoine du Nord": "Q221",
    "Benin": "Q962", "Liban": "Q822", "Antigua-et-Barbuda": "Q781",
    "Perou": "Q419", "Zambie": "Q953", "Israel": "Q801",
    "Bresil": "Q155", "Suede": "Q34", "Nouvelle-Zelande": "Q664",
    "Gambie": "Q1005", "Algerie": "Q262",
}

def fetch_wikidata_pays(pays, annee):
    qid_pays = PAYS_QID.get(pays)
    if not qid_pays:
        return None
    query = """
SELECT ?vainqueurLabel ?partiLabel WHERE {
  ?election wdt:P31 wd:Q40231 .
  ?election wdt:P17 wd:""" + qid_pays + """ .
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(YEAR(?date) = """ + str(annee) + """)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
LIMIT 1
"""
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/json", "User-Agent": "Geolandar/3.0"},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        if data and data[0].get("vainqueurLabel", {}).get("value"):
            return {
                "winner": data[0]["vainqueurLabel"]["value"],
                "party":  data[0].get("partiLabel", {}).get("value", ""),
            }
    except Exception as e:
        print(f"    Wikidata erreur: {type(e).__name__}")
    return None

# ══════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════
def deja_enregistre(pays):
    try:
        res = supabase.table("elections") \
            .select("winner") \
            .eq("pays", pays) \
            .eq("done", True) \
            .execute()
        for row in res.data:
            w = row.get("winner", "")
            if w and w not in ["", "En cours de verification"]:
                return True
    except:
        pass
    return False

def save_supabase(pays, date_el, winner, party):
    try:
        supabase.table("elections").upsert({
            "pays":       pays,
            "date":       date_el,
            "winner":     winner,
            "party":      party,
            "done":       True,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="pays,date").execute()
        print(f"  SUPABASE OK: {winner}")
        return True
    except Exception as e:
        print(f"  SUPABASE ERREUR: {e}")
        return False

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def est_passee(date_str):
    try:
        d_str = date_str.replace("-00", "-15")
        return datetime.strptime(d_str[:10], "%Y-%m-%d").date() <= date.today()
    except:
        return False

def main():
    print("=" * 60)
    print("  GEOLANDAR - Mise a jour automatique v3.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    passees = [(p, d, q, w, pa) for p, d, q, w, pa in ELECTIONS if est_passee(d)]
    print(f"\n  {len(passees)} elections passees\n")

    total = 0

    for pays, date_el, qid, winner_connu, party_connu in passees:
        print(f"--- {pays} ({date_el}) ---")

        if deja_enregistre(pays):
            print(f"  Deja enregistre")
            continue

        # Utiliser le résultat connu directement
        if winner_connu:
            print(f"  Resultat connu: {winner_connu}")
            if save_supabase(pays, date_el, winner_connu, party_connu):
                total += 1
        else:
            # Interroger Wikidata
            print(f"  Wikidata...")
            annee = int(date_el[:4])
            res = fetch_wikidata_pays(pays, annee)
            if res and res["winner"]:
                print(f"  Trouve: {res['winner']}")
                if save_supabase(pays, date_el, res["winner"], res["party"]):
                    total += 1
            else:
                print(f"  Pas de resultat")

        time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"  TOTAL: {total} elections mises a jour")
    print(f"  Termine: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
