# Diagnostic temporaire : récupère des échantillons des sources (supprimé après usage)
import requests, json, os
UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
os.makedirs("sonde", exist_ok=True)
def save(nom, txt): open("sonde/" + nom, "w").write(txt); print(nom, len(txt))
r = requests.get("https://www.cia.gov/resources/world-leaders/page-data/foreign-governments/page-data.json", headers=UA, timeout=60)
save("cia_index.json", r.text)
for h in r.json().get("staticQueryHashes", []):
    q = requests.get(f"https://www.cia.gov/resources/world-leaders/page-data/sq/d/{h}.json", headers=UA, timeout=60)
    save(f"cia_sq_{h}.json", q.text)
r = requests.get("https://www.cia.gov/resources/world-leaders/page-data/foreign-governments/serbia/page-data.json", headers=UA, timeout=60); save("cia_serbia.json", r.text)
for lang, page in [("fr", "Liste des dirigeants actuels des États"), ("en", "List of current heads of state and government")]:
    r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", params={"action": "parse", "page": page, "prop": "wikitext", "format": "json", "formatversion": 2}, headers=UA, timeout=60)
    save(f"wiki_{lang}.txt", r.json()["parse"]["wikitext"])
for page in ["Saeima", "Knesset", "National Assembly (Serbia)", "Senate (France)", "Bundestag"]:
    r = requests.get("https://en.wikipedia.org/w/api.php", params={"action": "parse", "page": page, "prop": "wikitext", "section": 0, "format": "json", "formatversion": 2, "redirects": 1}, headers=UA, timeout=60)
    save("leg_" + page.replace(" ", "_").replace("(", "").replace(")", "") + ".txt", r.json()["parse"]["wikitext"])
