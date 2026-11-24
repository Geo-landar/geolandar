# Diagnostic temporaire : pages Wikipédia des chambres non lues (supprimé après usage)
import requests, os, json
UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
os.makedirs("sonde", exist_ok=True)
pages = {"en": ["Lok Sabha", "House of Representatives (Indonesia)", "National Assembly of Pakistan", "Mäjilis", "Verkhovna Rada",
                "Senate of Canada", "Senate of Peru", "Chamber of Deputies of Peru", "Congress of the Republic of Peru", "Assembly of North Macedonia",
                "National Assembly (Namibia)", "Nitijela", "House of Assembly (Saint Vincent and the Grenadines)", "National Assembly (Saint Kitts and Nevis)"],
         "fr": ["Lok Sabha", "Conseil représentatif du peuple", "Assemblée nationale (Pakistan)", "Majilis", "Rada", "Sénat du Canada",
                "Sénat (Pérou)", "Chambre des députés (Pérou)", "Assemblée de la République de Macédoine du Nord", "Assemblée nationale (Namibie)"]}
for lang, ts in pages.items():
    for t in ts:
        try:
            r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
                "action": "parse", "page": t, "prop": "wikitext", "format": "json", "formatversion": 2, "redirects": 1}).json()
            w = r.get("parse", {}).get("wikitext", "") or json.dumps(r)[:500]
        except Exception as e:
            w = "ERREUR " + str(e)
        open(f"sonde/{lang}_" + t.replace(" ", "_").replace("/", "-") + ".txt", "w").write(w); print(lang, t, len(w))
