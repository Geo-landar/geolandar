# Diagnostic temporaire (supprimé après usage)
import requests, json, os
UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
os.makedirs("sonde", exist_ok=True)
def save(nom, txt): open("sonde/" + nom, "w").write(txt); print(nom, len(txt))
def wp(lang, **p):
    return requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=60, params={"format": "json", "formatversion": 2, **p}).json()
# 1. Listes de dirigeants régionaux en fonction
cats = {}
for c in ["Category:Lists of current office-holders", "Category:Lists of current governors", "Category:Lists of state governors"]:
    cats[c] = [m["title"] for m in wp("en", action="query", list="categorymembers", cmtitle=c, cmlimit=500).get("query", {}).get("categorymembers", [])]
save("cats.json", json.dumps(cats, ensure_ascii=False, indent=0))
recherches = {}
for q in ["List of current United States governors", "List of current Brazilian governors", "List of current Indian chief ministers",
          "List of current Mexican state governors", "List of current Argentine provincial governors", "List of current heads of federal subjects of Russia",
          "List of current state governors in Nigeria", "List of current Canadian first ministers", "List of current Australian premiers and chief ministers",
          "List of current German minister-presidents", "List of current Indonesian governors", "List of current Japanese governors",
          "List of current Colombian governors", "List of current Spanish regional presidents", "List of current Italian regional presidents",
          "Liste des présidents des conseils régionaux français", "List of current Pakistani chief ministers", "List of current Philippine governors",
          "List of current Peruvian regional governors", "List of current Chilean regional governors", "List of current Venezuelan governors",
          "List of current South Korean governors and mayors", "List of current Chinese provincial leaders", "List of current Kenyan governors"]:
    lang = "fr" if q.startswith("Liste") else "en"
    r = wp(lang, action="query", list="search", srsearch=q, srlimit=3)
    recherches[q] = [x["title"] for x in r.get("query", {}).get("search", [])]
save("recherches.json", json.dumps(recherches, ensure_ascii=False, indent=0))
for t in ["List of current United States governors", "List of current Indian chief ministers"]:
    save("liste_" + t.replace(" ", "_") + ".txt", wp("en", action="parse", page=t, prop="wikitext", redirects=1).get("parse", {}).get("wikitext", ""))
# 2. Fiches de régions (encadré) en lot
r = wp("en", action="query", prop="revisions", rvprop="content", rvslots="main", rvsection=0, titles="Bavaria|Lagos State|São Paulo (state)|Île-de-France|Ontario")
save("infobox_regions.json", json.dumps(r, ensure_ascii=False))
# 3. Wikipédia (fr) : chambres
for t in ["Saeima", "Knesset", "Sénat (France)", "Bundestag", "Assemblée nationale (Serbie)"]:
    save("fr_" + t.replace(" ", "_") + ".txt", wp("fr", action="parse", page=t, prop="wikitext", section=0, redirects=1).get("parse", {}).get("wikitext", ""))
# 4. Données officielles
for nom, u in [("uk_commons.json", "https://members-api.parliament.uk/api/Parties/StateOfTheParties/1/2026-11-13"),
               ("uk_lords.json", "https://members-api.parliament.uk/api/Parties/StateOfTheParties/2/2026-11-13"),
               ("abgw_periods.json", "https://www.abgeordnetenwatch.de/api/v2/parliament-periods?parliament=5&range_end=3"),
               ("nosdeputes.json", "https://www.nosdeputes.fr/organismes/groupe/json"),
               ("nossenateurs.json", "https://www.nossenateurs.fr/organismes/groupe/json")]:
    try:
        x = requests.get(u, headers=UA, timeout=60); save(nom, f"HTTP {x.status_code}\n" + x.text[:20000])
    except Exception as e: save(nom, "ERREUR " + str(e))
