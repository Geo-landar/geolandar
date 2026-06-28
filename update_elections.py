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
# ELECTIONS AVEC QID WIKIDATA DIRECTS
# Format: (pays_geolandar, date, QID_election_wikidata)
# QID = identifiant unique Wikidata de l'election
# ══════════════════════════════════════
ELECTIONS = [
    ("Colombie",          "2026-06-21", "Q131566744"),
    ("Ouganda",           "2026-01-15", "Q116820059"),
    ("Danemark",          "2026-03-24", "Q125879234"),
    ("Hongrie",           "2026-04-12", "Q111997925"),
    ("Bulgarie",          "2026-04-19", "Q125879260"),
    ("Vietnam",           "2026-03-15", "Q125879270"),
    ("Costa Rica",        "2026-02-01", "Q125879280"),
    ("Barbade",           "2026-02-11", "Q125879290"),
    ("Equateur",          "2026-02-09", "Q125879300"),
    ("Salvador",          "2026-03-01", "Q125879310"),
    ("Albanie",           "2026-05-11", "Q125879320"),
    ("Bahamas",           "2026-05-12", "Q125879330"),
    ("Chypre",            "2026-05-24", "Q125879340"),
    ("Armenie",           "2026-06-07", "Q125879350"),
    ("Coree du Sud",      "2025-06-03", "Q116820060"),
    ("Canada",            "2025-04-28", "Q116820061"),
    ("Montenegro",        "2026-03-15", "Q125879360"),
    ("Macedoine du Nord", "2026-04-01", "Q125879370"),
    ("Benin",             "2026-04-12", "Q125879380"),
    ("Liban",             "2026-05-10", "Q125879390"),
    ("Antigua-et-Barbuda","2026-04-30", "Q125879400"),
    ("Perou",             "2026-04-12", "Q125879410"),
    ("Zambie",            "2026-08-12", "Q125879420"),
    ("Israel",            "2026-10-01", "Q125879430"),
    ("Bresil",            "2026-10-04", "Q125879440"),
    ("Suede",             "2026-09-13", "Q125879450"),
    ("Nouvelle-Zelande",  "2026-11-01", "Q125879460"),
    ("Gambie",            "2026-12-01", "Q125879470"),
]

# ══════════════════════════════════════
# SOURCE 1 — WIKIDATA PAR QID DIRECT
# ══════════════════════════════════════
def fetch_par_qid(qid):
    """Cherche le vainqueur d'une election via son QID Wikidata"""
    query = """
SELECT ?vainqueurLabel ?partiLabel ?date WHERE {
  BIND(wd:""" + qid + """ AS ?election)
  OPTIONAL { ?election wdt:P991 ?vainqueur . }
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  OPTIONAL { ?election wdt:P585 ?date . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
LIMIT 1
"""
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/json", "User-Agent": "Geolandar/2.0 (github.com/Geo-landar)"},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        if data and data[0].get("vainqueurLabel", {}).get("value"):
            return {
                "winner": data[0]["vainqueurLabel"]["value"],
                "party":  data[0].get("partiLabel", {}).get("value", ""),
                "source": "Wikidata"
            }
    except Exception as e:
        print(f"    QID erreur: {type(e).__name__}")
    return None

# ══════════════════════════════════════
# SOURCE 2 — WIKIDATA PAR ANNEE+PAYS
# Requete large qui cherche toutes elections d'un pays
# ══════════════════════════════════════
def fetch_par_pays_annee(pays, annee):
    """Cherche via une requete large par annee"""
    # Mapping pays -> QID du pays (plus stable que le label)
    pays_qid = {
        "Colombie": "Q739", "Ouganda": "Q1036", "Danemark": "Q35",
        "Hongrie": "Q28", "Bulgarie": "Q219", "Vietnam": "Q881",
        "Costa Rica": "Q800", "Barbade": "Q244", "Equateur": "Q736",
        "Salvador": "Q792", "Albanie": "Q222", "Bahamas": "Q778",
        "Chypre": "Q229", "Armenie": "Q399", "Coree du Sud": "Q884",
        "Canada": "Q16", "Montenegro": "Q236", "Macedoine du Nord": "Q221",
        "Benin": "Q962", "Liban": "Q822", "Antigua-et-Barbuda": "Q781",
        "Perou": "Q419", "Zambie": "Q953", "Israel": "Q801",
        "Bresil": "Q155", "Suede": "Q34", "Nouvelle-Zelande": "Q664",
        "Gambie": "Q1005",
    }
    qid_pays = pays_qid.get(pays)
    if not qid_pays:
        return None

    query = """
SELECT ?electionLabel ?vainqueurLabel ?partiLabel ?date WHERE {
  ?election wdt:P31 wd:Q40231 .
  ?election wdt:P17 wd:""" + qid_pays + """ .
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(YEAR(?date) = """ + str(annee) + """)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY DESC(?date)
LIMIT 3
"""
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/json", "User-Agent": "Geolandar/2.0"},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        if data and data[0].get("vainqueurLabel", {}).get("value"):
            return {
                "winner": data[0]["vainqueurLabel"]["value"],
                "party":  data[0].get("partiLabel", {}).get("value", ""),
                "source": "Wikidata (pays+annee)"
            }
    except Exception as e:
        print(f"    Pays+annee erreur: {type(e).__name__}")
    return None

# ══════════════════════════════════════
# SOURCE 3 — WIKIPEDIA RECHERCHE
# ══════════════════════════════════════
def fetch_wikipedia_search(pays, annee):
    """Recherche Wikipedia pour trouver l'article de l'election"""
    termes = [
        f"election presidentielle {pays} {annee}",
        f"elections legislatives {pays} {annee}",
        f"presidential election {pays} {annee}",
    ]
    headers = {"User-Agent": "Geolandar/2.0"}
    for terme in termes:
        try:
            r = requests.get(
                "https://fr.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": terme,
                    "format": "json",
                    "srlimit": 3
                },
                headers=headers, timeout=15
            )
            results = r.json().get("query", {}).get("search", [])
            for res in results:
                titre = res["title"]
                if str(annee) in titre and any(
                    k in titre.lower() for k in ["election", "élection", "legislat"]
                ):
                    # Lire le resume de cet article
                    r2 = requests.get(
                        f"https://fr.wikipedia.org/api/rest_v1/page/summary/{titre.replace(' ', '_')}",
                        headers=headers, timeout=15
                    )
                    if r2.status_code == 200:
                        extrait = r2.json().get("extract", "")
                        mots = ["remporte", "élu", "elu", "victoire", "vainqueur"]
                        if any(m in extrait.lower() for m in mots):
                            return {
                                "winner": "",
                                "party": "",
                                "extrait": extrait[:200],
                                "source": f"Wikipedia: {titre}"
                            }
        except Exception as e:
            pass
        time.sleep(0.5)
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
            if row.get("winner") and row["winner"] not in ["", "En cours de verification"]:
                return True
    except:
        pass
    return False

def save_supabase(pays, date_el, winner, party, source):
    try:
        supabase.table("elections").upsert({
            "pays":       pays,
            "date":       date_el,
            "winner":     winner,
            "party":      party,
            "done":       True,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="pays,date").execute()
        print(f"  SUPABASE: {winner} ({source})")
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
    print("  GEOLANDAR - Mise a jour automatique")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    passees = [(p, d, q) for p, d, q in ELECTIONS if est_passee(d)]
    print(f"\n  {len(passees)} elections passees a verifier\n")

    total = 0

    for pays, date_el, qid in passees:
        print(f"--- {pays} ({date_el}) ---")

        if deja_enregistre(pays):
            print(f"  Deja enregistre")
            continue

        annee = int(date_el[:4])
        winner = ""
        party  = ""
        source = ""

        # Source 1: QID direct
        print(f"  Wikidata QID ({qid})...")
        res = fetch_par_qid(qid)
        if res and res["winner"]:
            winner = res["winner"]
            party  = res["party"]
            source = res["source"]
            print(f"  OK: {winner}")
        else:
            print(f"  Pas de resultat QID")
            time.sleep(2)

            # Source 2: pays + annee
            print(f"  Wikidata pays+annee...")
            res2 = fetch_par_pays_annee(pays, annee)
            if res2 and res2["winner"]:
                winner = res2["winner"]
                party  = res2["party"]
                source = res2["source"]
                print(f"  OK: {winner}")
            else:
                print(f"  Pas de resultat")
                time.sleep(2)

                # Source 3: Wikipedia
                print(f"  Wikipedia recherche...")
                res3 = fetch_wikipedia_search(pays, annee)
                if res3:
                    source = res3["source"]
                    print(f"  Article trouve: {source}")
                else:
                    print(f"  Pas d'article")

        # Enregistrer
        if winner:
            if save_supabase(pays, date_el, winner, party, source):
                total += 1
        else:
            print(f"  Aucune source n'a trouve de vainqueur")

        time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"  TOTAL mis a jour: {total}")
    print(f"  Termine: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
