# Diagnostic temporaire : teste les sources candidates (supprimé après usage)
import requests, json, re
UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
def get(url, **kw):
    try:
        r = requests.get(url, headers=UA, timeout=60, **kw)
        print(f"\n### {url[:140]} → HTTP {r.status_code}, {len(r.content)} octets, {r.headers.get('content-type','')}")
        return r
    except Exception as e:
        print(f"\n### {url[:140]} → ERREUR {e}"); return None

# 1. CIA World Leaders (Gatsby page-data)
for p in ["nepal", "netherlands", "thailand"]:
    r = get(f"https://www.cia.gov/resources/world-leaders/page-data/foreign-governments/{p}/page-data.json")
    if r is not None and r.ok:
        t = r.text; print(t[:1500])
r = get("https://www.cia.gov/resources/world-leaders/page-data/foreign-governments/page-data.json")
if r is not None and r.ok: print(r.text[:800])

# 2. Wikipédia EN : liste des chefs d'État et de gouvernement
r = get("https://en.wikipedia.org/w/api.php", params={"action": "parse", "page": "List of current heads of state and government", "prop": "wikitext", "format": "json", "formatversion": 2})
if r is not None and r.ok:
    w = r.json()["parse"]["wikitext"]
    for pays in ["Nepal", "Netherlands", "Thailand", "Serbia"]:
        i = w.find("[[" + pays); print(f"--- {pays}:", w[i:i+700].replace("\n", " ⏎ ") if i >= 0 else "absent")
# 3. Wikipédia FR
r = get("https://fr.wikipedia.org/w/api.php", params={"action": "parse", "page": "Liste des dirigeants actuels des États", "prop": "wikitext", "format": "json", "formatversion": 2})
if r is not None and r.ok:
    j = r.json()
    if "parse" in j:
        w = j["parse"]["wikitext"]; i = w.find("Népal"); print(w[:300].replace("\n"," ⏎ ")); print("--- Népal:", w[i:i+700].replace("\n", " ⏎ "))
    else: print(j)

# 4. IPU Parline
for u in ["https://api.data.ipu.org/v1/chambers/LV-LC", "https://api.data.ipu.org/v1/chambers?filter=country_code:eq:LV",
          "https://api.data.ipu.org/v1/metadata/fields?page[size]=400", "https://api.data.ipu.org/v1/elections?filter=country_code:eq:LV&sort=-election_date&page[size]=1"]:
    r = get(u)
    if r is not None: print(r.text[:2500])

# 5. Wikipédia : infobox d'une chambre (composition)
r = get("https://en.wikipedia.org/w/api.php", params={"action": "parse", "page": "Saeima", "prop": "wikitext", "section": 0, "format": "json", "formatversion": 2})
if r is not None and r.ok:
    w = r.json()["parse"]["wikitext"]; i = w.find("political_groups"); print(w[i:i+1500].replace("\n", " ⏎ "))
