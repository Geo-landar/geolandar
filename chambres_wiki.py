# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Répartition des sièges d'une chambre d'après Wikipédia (en)
#  (13/11/2026). Utilisé par update_regions.py, étape 4.
#
#  Lit l'infobox de l'article Wikipédia de la chambre : date de la dernière
#  élection et sièges par groupe (premier niveau de la liste). Écrit
#  seulement si la dernière élection est celle attendue (ou plus récente) et
#  si la somme des sièges est cohérente avec le total.
# ══════════════════════════════════════════════════════════════════
import re, requests

UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
MOIS_EN = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                            "august", "september", "october", "november", "december"])}

def wiki_en(params):
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=60,
                     params={"format": "json", "formatversion": 2, **params})
    r.raise_for_status()
    return r.json()

def sans_modeles(t, noms):
    """Retire notes et modèles {{efn…}} (imbrications comprises)."""
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    motif = re.compile(r"\{\{\s*(" + "|".join(re.escape(n) for n in noms) + r")\s*[|}]", re.I)
    out, i = [], 0
    while i < len(t):
        if t.startswith("{{", i) and motif.match(t, i):
            d, j = 0, i
            while j < len(t):
                if t.startswith("{{", j):
                    d += 1; j += 2; continue
                if t.startswith("}}", j):
                    d -= 1; j += 2
                    if d == 0: break
                    continue
                j += 1
            i = j; continue
        out.append(t[i]); i += 1
    return "".join(out)

def champ(t, nom):
    m = re.search(r"\|\s*" + nom + r"\s*=(.*?)(?=\n\s*\|\s*[a-z_0-9]+\s*=|\n\}\})", t, re.S)
    return m.group(1) if m else ""

def date_en(t):
    t = t or ""
    m = re.search(r"end date\|(\d{4})\|(\d{1,2})\|(\d{1,2})", t, re.I)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2}) ([A-Z][a-z]+) (\d{4})", t)
    if m and m.group(2).lower() in MOIS_EN: return f"{m.group(3)}-{MOIS_EN[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", t)
    if m and m.group(1).lower() in MOIS_EN: return f"{m.group(3)}-{MOIS_EN[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return ""

COLOR_BOX = re.compile(r"\{\{\s*Colou?r ?box\s*\|\s*(#[0-9A-Fa-f]{3,6}|\{\{\s*party colou?r\s*\|[^}]+\}\})[^{}]*(?:\{\{[^}]*\}\}[^{}]*)*\}\}", re.I)

def analyser(t):
    """Wikitexte de l'en-tête de l'article → (date dernière élection, groupes, total indiqué)."""
    t = sans_modeles(t, ["efn", "refn", "efn-lr", "efn-ua", "sfn", "cn", "citation needed", "update needed", "dubious"])
    derniere = max([date_en(champ(t, k)) for k in ("last_election1", "last_election", "last_election2")] or [""])
    blocs = [champ(t, k) for k in ("political_groups1", "political_groups", "political_groups2")]
    bloc = next((b for b in blocs if re.search(r"\(\d+\)", b)), "")
    tot = re.search(r"\d+", re.sub(r"<[^>]+>", "", champ(t, "seats1") or champ(t, "seats") or ""))
    entrees = []
    for ligne in bloc.split("\n"):
        m = re.match(r"^\s*\|?\s*([*:#]+)\s*(.*)$", ligne)
        if not m: continue
        niveau, txt = len(m.group(1)), m.group(2).strip()
        n = re.search(r"\((?:\[\[[^\]|]*\|)?(\d+)(?:\]\])?\)\s*(?:\}\})?\s*$", txt)
        if not n: continue
        cb = COLOR_BOX.search(txt)
        reste = COLOR_BOX.sub("", txt[:n.start()]).strip()
        lien = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", reste)
        if lien:
            nom, sigle = lien.group(1).strip(), (lien.group(2) or "").strip()
        else:
            nom, sigle = re.sub(r"\[\[|\]\]|\{\{[^}]*\}\}|'{2,}", "", reste).strip(), ""
        nom = re.sub(r"\s*\([^)]*\)$", "", nom.split("#")[-1]).strip()
        sigle = re.sub(r"'{2,}", "", sigle).strip()
        if not nom: continue
        entrees.append({"niveau": niveau, "lien": nom, "sigle": sigle, "s": int(n.group(1)),
                        "couleur": cb.group(1).strip() if cb else ""})
    total = int(tot.group()) if tot else None
    if not entrees: return derniere, [], total
    haut = min(e["niveau"] for e in entrees)
    return derniere, [e for e in entrees if e["niveau"] == haut], total

def lire_infobox(titre):
    t = wiki_en({"action": "parse", "page": titre, "prop": "wikitext", "section": 0, "redirects": 1})["parse"]["wikitext"]
    return analyser(t)

def couleurs(modeles):
    """{{party color|X}} → #rrggbb (un seul appel à l'API pour tous)."""
    res = {m: m for m in modeles if m.startswith("#")}
    a_traduire = sorted({m for m in modeles if m.startswith("{{")})
    if a_traduire:
        try:
            txt = wiki_en({"action": "expandtemplates", "text": "§".join(a_traduire), "prop": "wikitext"})["expandtemplates"]["wikitext"]
            for m, c in zip(a_traduire, txt.split("§")):
                c = c.strip()
                if re.match(r"^#?[0-9A-Fa-f]{6}$", c): res[m] = c if c.startswith("#") else "#" + c
        except Exception:
            pass
    return res

# ── Wikipédia en français : encadré « Infobox Parlement » ({{Légende|couleur|[[groupe|sigle]] (n)}})
MOIS_FR = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
           "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12}

def date_fr(t):
    t = re.sub(r"[{}|\[\]]", " ", t or "")
    m = re.search(r"(\d{1,2})(?:er)?\s+([a-zéû]+)\s+(\d{4})", t, re.I)
    if m and m.group(2).lower() in MOIS_FR:
        return f"{m.group(3)}-{MOIS_FR[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return ""

def analyser_fr(t):
    t = sans_modeles(t, ["note", "refnec", "référence nécessaire", "efn"])
    derniere = max([date_fr(champ(t, k)) for k in ("dernière_élection1", "dernière_élection", "dernière_élection2")] or [""])
    groupes = []
    for ligne in t.split("\n"):
        m = re.match(r"^\s*(\**)\s*\{\{\s*Légende\s*\|(.*)\((\d+)\)\s*\}\}\s*$", ligne)
        if not m or m.group(1): continue                     # sous-groupes (« * ») ignorés
        corps = m.group(2)
        lien = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", corps)
        nom = (lien.group(1) if lien else re.sub(r"^.*\|", "", corps)).strip()
        sigle = (lien.group(2) or "").strip() if lien else ""
        coul = corps.split("|")[0].strip()
        groupes.append({"lien": re.sub(r"\s*\([^)]*\)$", "", nom), "sigle": sigle, "s": int(m.group(3)), "couleur": coul})
    return derniere, groupes

def lire_infobox_fr(titre):
    r = requests.get("https://fr.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
        "format": "json", "formatversion": 2, "action": "parse", "page": titre, "prop": "wikitext", "section": 0, "redirects": 1})
    r.raise_for_status()
    return analyser_fr(r.json()["parse"]["wikitext"])

def couleurs_fr(modeles):
    res = {m: m for m in modeles if m.startswith("#")}
    a_traduire = sorted({m for m in modeles if m.startswith("{{")})
    if a_traduire:
        try:
            r = requests.get("https://fr.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
                "format": "json", "formatversion": 2, "action": "expandtemplates", "text": "§".join(a_traduire), "prop": "wikitext"})
            for m, c in zip(a_traduire, r.json()["expandtemplates"]["wikitext"].split("§")):
                c = c.strip()
                if re.match(r"^#?[0-9A-Fa-f]{6}$", c): res[m] = c if c.startswith("#") else "#" + c
        except Exception:
            pass
    return res

# ── Sources officielles (mises à jour en continu, pas seulement après une élection)
def officiel_communes_uk():
    """Chambre des communes : répartition officielle (API du Parlement britannique)."""
    from datetime import date
    r = requests.get(f"https://members-api.parliament.uk/api/Parties/StateOfTheParties/1/{date.today().isoformat()}", headers=UA, timeout=60)
    r.raise_for_status()
    return [{"lien": x["value"]["party"]["name"], "sigle": x["value"]["party"].get("abbreviation") or "",
             "s": x["value"]["total"], "couleur": "#" + (x["value"]["party"].get("backgroundColour") or "94a3b8")}
            for x in r.json()["items"] if x["value"]["total"] > 0]

def officiel_assemblee_fr():
    """Assemblée nationale : députés en mandat par groupe (NosDéputés.fr, données de l'Assemblée)."""
    org = requests.get("https://www.nosdeputes.fr/organismes/groupe/json", headers=UA, timeout=60).json()
    groupes = {}
    for o in org.get("organismes", []):
        o = o["organisme"]
        if o.get("groupe_actuel"):
            rgb = [int(x) for x in (o.get("couleur") or "148,163,184").split(",")]
            groupes[o["acronyme"]] = {"lien": o["nom"], "sigle": o["acronyme"], "s": 0, "couleur": "#%02x%02x%02x" % tuple(rgb[:3])}
    deps = requests.get("https://www.nosdeputes.fr/deputes/enmandat/json", headers=UA, timeout=60).json()
    for d in deps.get("deputes", []):
        g = d["depute"].get("groupe_sigle")
        if g in groupes: groupes[g]["s"] += 1
    return [g for g in groupes.values() if g["s"] > 0]

OFFICIELS = {("Royaume-Uni", "House of Commons"): officiel_communes_uk,
             ("France", "Assemblée nationale"): officiel_assemblee_fr}
