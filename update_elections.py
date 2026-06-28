import requests
from supabase import create_client
from datetime import datetime, date
import time
import os

# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtYnVweXl1Z2VkbXRtdnphZGVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU4NTM3MTIsImV4cCI6MjA2MTQyOTcxMn0.mwb7OrlLLq0PaPMzqBV8KWIzaALhFy3AoXLuuiCMXmAAM")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════
# ELECTIONS A SURVEILLER
# (pays, date, page Wikipedia FR exacte)
# ══════════════════════════════════════
ELECTIONS = [
    ("Colombie",         "2026-06-21", "Election_presidentielle_colombienne_de_2026"),
    ("Perou",            "2026-04-12", "Election_presidentielle_peruvienne_de_2026"),
    ("Ouganda",          "2026-01-15", "Election_presidentielle_ougandaise_de_2026"),
    ("Danemark",         "2026-03-24", "Elections_legislatives_danoises_de_2026"),
    ("Hongrie",          "2026-04-12", "Elections_legislatives_hongroises_de_2026"),
    ("Bulgarie",         "2026-04-19", "Elections_legislatives_bulgares_de_2026"),
    ("Vietnam",          "2026-03-15", "Elections_legislatives_vietnamiennes_de_2026"),
    ("Costa Rica",       "2026-02-01", "Election_presidentielle_costaricienne_de_2026"),
    ("Barbade",          "2026-02-11", "Elections_legislatives_de_la_Barbade_de_2026"),
    ("Antigua-et-Barbuda","2026-04-30","Elections_generales_d_Antigua-et-Barbuda_de_2026"),
    ("Equateur",         "2026-02-09", "Election_presidentielle_equatorienne_de_2026"),
    ("Salvador",         "2026-03-01", "Elections_legislatives_du_Salvador_de_2026"),
    ("Albanie",          "2026-05-11", "Elections_legislatives_albanaises_de_2026"),
    ("Bahamas",          "2026-05-12", "Elections_generales_des_Bahamas_de_2026"),
    ("Chypre",           "2026-05-24", "Elections_legislatives_chypriotes_de_2026"),
    ("Armenie",          "2026-06-07", "Elections_legislatives_armeniennes_de_2026"),
    ("Coree du Sud",     "2025-06-03", "Election_presidentielle_sud-coreenne_de_2025"),
    ("Canada",           "2025-04-28", "Elections_federales_canadiennes_de_2025"),
    ("Bangladesh",       "2026-02-28", "Elections_legislatives_bangladaises_de_2026"),
    ("Montenegro",       "2026-03-15", "Elections_legislatives_montenegrines_de_2026"),
    ("Macedoine du Nord","2026-04-01", "Elections_legislatives_macedoniennes_de_2026"),
    ("Benin",            "2026-04-12", "Election_presidentielle_beninoise_de_2026"),
    ("Liban",            "2026-05-10", "Elections_legislatives_libanaises_de_2026"),
    ("Zambie",           "2026-08-12", "Election_presidentielle_zambienne_de_2026"),
    ("Israel",           "2026-10-01", "Elections_legislatives_israeliennes_de_2026"),
    ("Bresil",           "2026-10-04", "Election_presidentielle_bresilienne_de_2026"),
    ("Suede",            "2026-09-13", "Elections_legislatives_suedoises_de_2026"),
    ("Nouvelle-Zelande", "2026-11-01", "Elections_generales_neo-zelandaises_de_2026"),
    ("Gambie",           "2026-12-01", "Election_presidentielle_gambienne_de_2026"),
]

# ══════════════════════════════════════
# SOURCE 1 — WIKIDATA
# ══════════════════════════════════════
def fetch_wikidata(pays, annee):
    """Requete Wikidata avec plusieurs variantes du nom de pays"""
    noms_pays = {
        "Coree du Sud": ["Corée du Sud", "Korea"],
        "Macedoine du Nord": ["Macédoine du Nord", "North Macedonia"],
        "Antigua-et-Barbuda": ["Antigua-et-Barbuda", "Antigua and Barbuda"],
    }
    labels = noms_pays.get(pays, [pays])

    for label in labels:
        query = """
SELECT ?vainqueurLabel ?partiLabel ?date WHERE {
  ?election wdt:P31 wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?pays rdfs:label \"""" + label + """\"@fr .
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
                headers={"Accept": "application/json", "User-Agent": "Geolandar/1.0"},
                timeout=30
            )
            r.raise_for_status()
            data = r.json()["results"]["bindings"]
            if data:
                return {
                    "winner": data[0].get("vainqueurLabel", {}).get("value", ""),
                    "party":  data[0].get("partiLabel", {}).get("value", ""),
                    "source": "Wikidata"
                }
        except Exception as e:
            pass
        time.sleep(2)
    return None

# ══════════════════════════════════════
# SOURCE 2 — WIKIPEDIA API
# ══════════════════════════════════════
def fetch_wikipedia(page_titre):
    """Lit le resume Wikipedia d'une election"""
    try:
        url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{page_titre}"
        r = requests.get(url, headers={"User-Agent": "Geolandar/1.0"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            extrait = data.get("extract", "")
            # L'article existe et mentionne une victoire
            mots = ["remporte", "elu", "elu president", "victoire", "vainqueur", "gagne"]
            if any(m in extrait.lower() for m in mots):
                return {
                    "winner": "",  # extrait seul sans nom exact
                    "party":  "",
                    "extrait": extrait[:300],
                    "source": "Wikipedia"
                }
    except Exception as e:
        pass
    return None

# ══════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════
def deja_enregistre(pays):
    """Verifie si une election est deja dans Supabase avec un vainqueur"""
    try:
        res = supabase.table("elections") \
            .select("winner") \
            .eq("pays", pays) \
            .eq("done", True) \
            .neq("winner", "") \
            .execute()
        return len(res.data) > 0
    except:
        return False

def save_supabase(pays, date_el, winner, party, source):
    """Enregistre le resultat dans Supabase"""
    try:
        supabase.table("elections").upsert({
            "pays":       pays,
            "date":       date_el,
            "winner":     winner,
            "party":      party,
            "done":       True,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="pays,date").execute()
        print(f"  SUPABASE OK: {winner} via {source}")
        return True
    except Exception as e:
        print(f"  SUPABASE ERREUR: {e}")
        return False

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def est_passee(date_str):
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date() <= date.today()
    except:
        return False

def main():
    print("=" * 60)
    print("  GEOLANDAR - Mise a jour automatique")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    passees = [(p, d, w) for p, d, w in ELECTIONS if est_passee(d)]
    print(f"\n  {len(passees)} elections passees a verifier\n")

    total = 0

    for pays, date_el, wiki_page in passees:
        print(f"--- {pays} ({date_el}) ---")

        # Deja dans Supabase ?
        if deja_enregistre(pays):
            print(f"  Deja enregistre, on passe")
            continue

        annee = int(date_el[:4])
        winner = ""
        party  = ""
        source = ""

        # Source 1 : Wikidata
        print(f"  Wikidata...")
        res = fetch_wikidata(pays, annee)
        if res and res["winner"]:
            winner = res["winner"]
            party  = res["party"]
            source = "Wikidata"
            print(f"  OK: {winner}")
        else:
            print(f"  Pas de resultat")

        # Source 2 : Wikipedia (si Wikidata vide)
        if not winner:
            print(f"  Wikipedia...")
            res2 = fetch_wikipedia(wiki_page)
            if res2:
                source = "Wikipedia (article existe)"
                print(f"  Article trouve mais vainqueur non extrait")
            else:
                print(f"  Pas d'article")

        # Enregistrer dans Supabase
        if winner:
            if save_supabase(pays, date_el, winner, party, source):
                total += 1
        elif source:
            # Article Wikipedia existe : marquer done sans vainqueur pour l'instant
            save_supabase(pays, date_el, "En cours de verification", "", source)

        time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"  TOTAL mis a jour: {total}")
    print(f"  Termine: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
