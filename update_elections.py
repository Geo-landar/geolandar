import requests
from supabase import create_client
from datetime import datetime
import time
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

WIKIDATA_QUERY = """
SELECT ?paysLabel ?date ?vainqueurLabel ?partiLabel WHERE {
  ?election wdt:P31 wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election wdt:P585 ?date .
  OPTIONAL { ?election wdt:P991 ?vainqueur . }
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(?date >= "2025-01-01"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY DESC(?date)
LIMIT 50
"""

def fetch_wikidata():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Interrogation Wikidata...")
    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/json", "User-Agent": "Geolandar/1.0"}
    for tentative in range(1, 4):
        try:
            print(f"  Tentative {tentative}/3...")
            r = requests.get(url, params={"query": WIKIDATA_QUERY, "format": "json"},
                           headers=headers, timeout=60)
            r.raise_for_status()
            resultats = r.json()["results"]["bindings"]
            print(f"  OK: {len(resultats)} resultats")
            return resultats
        except Exception as e:
            print(f"  Echec: {type(e).__name__}")
            if tentative < 3:
                time.sleep(15)
    return []

def update_supabase(resultats):
    count = 0
    for r in resultats:
        try:
            pays = r.get("paysLabel", {}).get("value", "")
            date = r.get("date", {}).get("value", "")[:10]
            if not pays or not date:
                continue
            supabase.table("elections").upsert({
                "pays": pays,
                "date": date,
                "winner": r.get("vainqueurLabel", {}).get("value", ""),
                "party": r.get("partiLabel", {}).get("value", ""),
                "done": True,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="pays,date").execute()
            count += 1
            print(f"  OK: {pays} ({date})")
        except Exception as e:
            print(f"  Erreur: {e}")
    return count

def main():
    print("=" * 50)
    print("GEOLANDAR - Mise a jour elections")
    print(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)
    resultats = fetch_wikidata()
    if resultats:
        total = update_supabase(resultats)
        print(f"\nTotal: {total} mises a jour Supabase")
    else:
        print("Aucun resultat - Wikidata indisponible")
    print(f"Termine: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
