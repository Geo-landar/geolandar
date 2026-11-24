# Diagnostic temporaire : encadrés des articles d'élections (supprimé après usage)
import requests, os, re
UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
os.makedirs("sonde", exist_ok=True)
pages = {"en": ["2026 Latvian parliamentary election", "2026 Israeli legislative election", "2026 Serbian parliamentary election",
                "2026 New Zealand general election", "2025 Dutch general election", "2025 German federal election", "2026 Grenadian general election"],
         "fr": ["Élections législatives lettones de 2026", "Élections législatives israéliennes de 2026", "Élections législatives serbes de 2026",
                "Élections législatives néo-zélandaises de 2026", "Élections législatives néerlandaises de 2025", "Élections fédérales allemandes de 2025"]}
for lang, ts in pages.items():
    for t in ts:
        try:
            r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
                "action": "parse", "page": t, "prop": "wikitext", "section": 0, "format": "json", "formatversion": 2, "redirects": 1}).json()
            w = r.get("parse", {}).get("wikitext", "") or str(r)[:300]
        except Exception as e: w = "ERREUR " + str(e)
        open(f"sonde/{lang}_" + re.sub(r"\W+", "_", t) + ".txt", "w").write(w); print(lang, t, len(w))
