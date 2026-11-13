# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Sources complémentaires à Wikidata pour les dirigeants
#  régionaux (13/11/2026). Utilisé par update_regions.py.
#
#  1. Listes Wikipédia (en) des dirigeants régionaux en fonction, pays par
#     pays (gouverneurs, chefs de gouvernement des États…), avec la date de
#     prise de fonction.
#  2. Encadré (infobox) de l'article Wikipédia (en) de chaque région :
#     dirigeant actuel, présenté de la même façon pour tous les pays.
# ══════════════════════════════════════════════════════════════════
import re, requests

UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}

# Page Wikipédia (en) listant les dirigeants régionaux en fonction, par pays du site
LISTES = {
    "Etats-Unis": "List of current United States governors",
    "Bresil": "List of current state governors in Brazil",
    "Mexique": "List of current state governors in Mexico",
    "Argentine": "List of provincial governors in Argentina",
    "Russie": "List of heads of federal subjects of Russia",
    "Nigeria": "List of current state governors in Nigeria",
    "Canada": "List of current first ministers of Canada",
    "Australie": "Premiers and chief ministers of the Australian states and territories",
    "Indonesie": "List of current Indonesian governors",
    "Japon": "List of current Japanese governors",
    "Espagne": "List of current presidents of the autonomous communities of Spain",
    "Philippines": "List of current Philippine governors",
    "Coree du Sud": "List of current South Korean mayors and governors",
    "Inde": "Chief minister (India)",
    "Pakistan": "Chief minister (Pakistan)",
    "Allemagne": "Minister president (Germany)",
    "France": "List of current presidents of the regional councils of France and the Corsican Assembly",
}

MOIS_EN = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                            "august", "september", "october", "november", "december"])}
NON_PERSONNE = re.compile(r"(^(file|image|fichier|category|list)\b|party|parti|partido|congress|alliance|front|"
                          r"union|movement|league|coalition|governor|minister|president|premier|council|assembly|"
                          r"province|state|region|independent|politician|democrat|republican|liberal|labou?r|"
                          r"conservative|socialist|communist|national|people)", re.I)

def wiki(params, lang="en"):
    r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=60,
                     params={"format": "json", "formatversion": 2, **params})
    r.raise_for_status()
    return r.json()

def sans_notes(t):
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)

def date_ligne(t):
    m = re.search(r"\{\{\s*(?:dts|start date(?: and age)?|sda|date)\s*\|(?:[a-z]+=[^|}]*\|)*\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", t, re.I)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"\b(\d{1,2}) ([A-Z][a-z]+) (\d{4})\b", t)
    if m and m.group(2).lower() in MOIS_EN: return f"{m.group(3)}-{MOIS_EN[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"\b([A-Z][a-z]+) (\d{1,2}), (\d{4})\b", t)
    if m and m.group(1).lower() in MOIS_EN: return f"{m.group(3)}-{MOIS_EN[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return ""

def personnes(t):
    """Noms de personnes d'un morceau de wikitexte : {{sortname|Prénom|Nom}} et liens [[…]]."""
    noms = []
    for m in re.finditer(r"\{\{\s*sortname\s*\|([^|}]+)\|([^|}]+)", t, re.I):
        noms.append(f"{m.group(1).strip()} {m.group(2).strip()}")
    for m in re.finditer(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", t):
        cible = m.group(1).strip()
        if NON_PERSONNE.search(cible) or re.search(r"\d|\bof\b|district|emblem|flag|seal|coat of arms", cible, re.I): continue
        if len(cible.split()) < 2 and not re.match(r"^[A-Z][a-z]+$", cible): continue
        noms.append(re.sub(r"\s*\([^)]*\)$", "", cible))
    return noms

def lire_liste(titre, alias, norm_region):
    """{nom de région du site: (titulaire, date de prise de fonction)} d'après une liste Wikipédia.
    alias : {nom normalisé (français, anglais, titre d'article…): nom de région du site}."""
    t = sans_notes(wiki({"action": "parse", "page": titre, "prop": "wikitext", "redirects": 1})["parse"]["wikitext"])
    cible = alias
    res = {}
    for ligne in t.split("\n|-"):
        reg = None
        for m in re.finditer(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", ligne):
            for x in (m.group(2), m.group(1)):
                k = norm_region(re.sub(r"\s*\([^)]*\)$", "", x or ""))
                k2 = norm_region(re.sub(r"^(governor|chief minister|premier|minister president|president) of ", "", (x or "").strip(), flags=re.I))
                if k in cible or k2 in cible:
                    reg = cible.get(k) or cible.get(k2); break
            if reg: break
        if not reg or reg in res: continue
        noms = [n for n in personnes(ligne) if norm_region(n) not in cible]
        if noms:
            res[reg] = (noms[0], date_ligne(ligne))
    return res

def lire_infobox(titres):
    """{titre: [noms des dirigeants cités dans l'encadré]} — 50 articles par appel."""
    res = {}
    titres = sorted(set(titres))
    for i in range(0, len(titres), 50):
        lot = titres[i:i + 50]
        try:
            d = wiki({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                      "rvsection": 0, "titles": "|".join(lot), "redirects": 1})
        except Exception:
            continue
        renvois = {r["to"]: r["from"] for r in d.get("query", {}).get("redirects", [])}
        norm = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
        for p in d.get("query", {}).get("pages", []):
            try: t = sans_notes(p["revisions"][0]["slots"]["main"]["content"])
            except (KeyError, IndexError): continue
            noms = []
            for m in re.finditer(r"\|\s*(?:leader_name1?|governor|premier|leader|head|chief_minister|president)\s*=([^\n]*)", t, re.I):
                noms += personnes(m.group(1))
            titre = renvois.get(p["title"], p["title"]); titre = norm.get(titre, titre)
            res[titre] = noms
    return res
