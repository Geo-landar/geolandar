# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Sources complémentaires à Wikidata pour les dirigeants
#  (13/11/2026). Utilisé par update_dirigeants.py.
#
#  1. Wikipédia (fr) « Liste des dirigeants actuels des États » : tenue à
#     jour en quelques heures, avec la DATE de prise de fonction.
#  2. CIA World Leaders (gouvernement américain, domaine public) : annuaire
#     officiel des chefs d'État et de gouvernement, mis à jour régulièrement.
#
#  Règle (dans update_dirigeants.py) : le titulaire le plus récent l'emporte,
#  à condition d'être confirmé par une deuxième source indépendante.
# ══════════════════════════════════════════════════════════════════
import re, unicodedata, requests

UA = {"User-Agent": "Geolandar/2.2 (https://geolandar.fr; contact@geolandar.fr)"}

def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip()

VIDES = {"bin", "ben", "ibn", "al", "el", "de", "da", "du", "von", "van", "der", "prince", "roi", "sheikh", "cheikh",
         "abdel", "abdul", "mohammed", "muhammad", "mohamed", "ahmed", "ali", "jean", "jr", "acting"}

def meme_personne(a, b):
    """Même règle que le site (memePersonneNoms) : un mot significatif commun, ou noms très proches."""
    A, B = norm(a), norm(b)
    if not A or not B: return False
    if A == B: return True
    ta = {t for t in A.split() if len(t) >= 4 and t not in VIDES}
    tb = {t for t in B.split() if len(t) >= 4 and t not in VIDES}
    if ta & tb: return True
    def bg(s):
        r = {}
        for i in range(len(s) - 1): r[s[i:i + 2]] = r.get(s[i:i + 2], 0) + 1
        return r
    x, y = bg(A.replace(" ", "")), bg(B.replace(" ", ""))
    inter = sum(min(n, y.get(k, 0)) for k, n in x.items())
    tot = sum(x.values()) + sum(y.values())
    return tot > 0 and 2 * inter / tot >= 0.6

MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}

def _date_fr(txt):
    m = re.search(r"\{\{\s*date\s*\|([^}]*)\}\}", txt or "", re.I)
    if not m: return ""
    p = [x.strip() for x in m.group(1).replace("|", " ").split() if x.strip()]
    p = [x for x in p if not x.startswith(("age", "en"))]
    if len(p) >= 3 and p[0].isdigit() and norm(p[1]) in MOIS and p[2][:4].isdigit():
        return f"{p[2][:4]}-{MOIS[norm(p[1])]:02d}-{int(p[0]):02d}"
    return ""

def _lien(txt):
    """Premier lien [[cible|texte]] → texte affiché."""
    sv = re.search(r"\{\{\s*Souverain\d?\s*\|([^}|]+)", txt or "")
    if sv: return re.sub(r"\s*\(.*\)", "", sv.group(1)).strip()
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", txt or "")
    return (m.group(2) or m.group(1)).strip() if m else re.sub(r"[\[\]{}'|]", "", txt or "").strip()

def _sans_notes(t):
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)

def wikipedia_fr(pays_depuis_nom):
    """{pays_site: [{"fonction", "nom", "debut"}]} — pays_depuis_nom(nom_fr) → nom du site ou None."""
    r = requests.get("https://fr.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "parse", "page": "Liste des dirigeants actuels des États", "prop": "wikitext",
        "format": "json", "formatversion": 2})
    r.raise_for_status()
    texte = _sans_notes(r.json()["parse"]["wikitext"])
    texte = texte.split("== Gouvernements alternatifs")[0]          # États reconnus et « autres États » seulement
    res, pays, inconnus = {}, None, set()
    for ligne in texte.split("\n|-"):
        ligne = ligne.strip()
        if not ligne.startswith("|") or ligne.startswith("|}"): continue
        brutes = [c.strip() for c in ligne.lstrip("|").split("||")]
        cellules = [re.sub(r'^(rowspan|colspan|style|align)\s*=\s*"?[^"|]*"?\s*\|', "", c).strip() for c in brutes]
        m = re.match(r"^\{\{([^}|]+)\}\}$", cellules[0])
        f = re.match(r"^\[\[(?:Fichier|File|Image):[^\]]*\]\]\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]$", cellules[0])
        if (m or f) and len(cellules) >= 3:
            nom_pays = (m or f).group(1).strip()
            pays = pays_depuis_nom(nom_pays)
            if not pays: inconnus.add(nom_pays)
            cellules = cellules[1:]
        elif brutes[0].startswith("rowspan") and len(cellules) >= 3:
            pays = None                                    # pays non reconnu : on n'attribue pas ses lignes au précédent
        if not pays or len(cellules) < 2: continue
        fonction, nom = cellules[0], cellules[1]
        debut = _date_fr(cellules[2]) if len(cellules) > 2 else ""
        nom = _lien(nom)
        if not nom or re.search(r"\d", nom) or nom.lower().startswith(("vacant", "poste vacant")): continue
        res.setdefault(pays, []).append({"fonction": re.sub(r"\s+", " ", _lien(fonction) + " " + re.sub(r"\[\[[^\]]*\]\]", "", fonction)).strip(),
                                         "nom": nom, "debut": debut})
    return res, inconnus

CHEF_GOUV = re.compile(r"premier ministre|chef du gouvernement|president du gouvernement|chancelier|taoiseach|"
                       r"president du conseil|ministre d etat|premier|prime minister", re.I)

def choisir_fr(lignes, role):
    """Ligne correspondant au rôle affiché : 'hog' (chef du gouvernement) ou 'hos' (chef de l'État)."""
    if role == "hog":
        c = [l for l in lignes if CHEF_GOUV.search(norm(l["fonction"]))]
    else:
        c = [l for l in lignes if not CHEF_GOUV.search(norm(l["fonction"]))
             and not re.search(r"vice|gouverneur general|adjoint|representant", norm(l["fonction"]))]
    return c[0] if len(c) == 1 else None

EN_PAYS = {"The Bahamas": "bs", "Bahamas": "bs", "The Gambia": "gm", "Gambia": "gm", "Myanmar": "mm",
           "Democratic Republic of the Congo": "cd", "Republic of the Congo": "cg", "Ivory Coast": "ci",
           "East Timor": "tl", "Timor-Leste": "tl", "Vatican City": "va", "North Korea": "kp", "South Korea": "kr",
           "Federated States of Micronesia": "fm", "Micronesia": "fm", "Cape Verde": "cv", "Eswatini": "sz",
           "Russia": "ru", "Iran": "ir", "Syria": "sy", "Laos": "la", "Vietnam": "vn", "Bolivia": "bo",
           "Venezuela": "ve", "Tanzania": "tz", "Moldova": "md", "Brunei": "bn", "Turkey": "tr", "Czech Republic": "cz",
           "Czechia": "cz", "Kosovo": "xk", "Taiwan": "tw", "Somaliland": "", "São Tomé and Príncipe": "st",
           "Sao Tome and Principe": "st", "Netherlands": "nl", "Kingdom of the Netherlands": "nl", "Denmark": "dk",
           "Kingdom of Denmark": "dk", "Georgia": "ge", "Georgia (country)": "ge", "Switzerland": "ch", "United States": "us", "United Kingdom": "gb", "Palestine": "", "State of Palestine": ""}

def iso_anglais(nom):
    if nom in EN_PAYS: return EN_PAYS[nom]
    if nom in CIA_ISO: return CIA_ISO[nom]
    try:
        import pycountry
        try: return pycountry.countries.lookup(nom).alpha_2.lower()
        except LookupError: return pycountry.countries.search_fuzzy(nom)[0].alpha_2.lower()
    except Exception:
        return ""

def wikipedia_en(pays_depuis_iso):
    """{pays_site: [noms]} — tous les dirigeants cités pour le pays (« List of current heads of state and government »)."""
    r = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "parse", "page": "List of current heads of state and government", "prop": "wikitext",
        "format": "json", "formatversion": 2})
    r.raise_for_status()
    texte = _sans_notes(r.json()["parse"]["wikitext"]).split("==Other states==")[0]
    res, pays = {}, None
    for ligne in texte.split("\n"):
        m = re.search(r"\{\{flag\|([^}|]+)", ligne)
        if ligne.startswith("!") and m:
            pays = pays_depuis_iso(iso_anglais(m.group(1).strip())); continue
        if not pays or not ligne.startswith("|") or ligne.startswith("|-"): continue
        for nom in re.findall(r"[–-]\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", ligne):
            res.setdefault(pays, []).append((nom[1] or nom[0]).strip())
    return res

CIA_TITRES = re.compile(r"^(pres|king|queen|emir|sultan|amir|prince|grand duke|chmn|chairman|supreme leader|prime min|"
                        r"premier|chancellor|head of govt|chief exec|co-prince|captain regent|pope|gen\. sec)", re.I)

def cia(pays_depuis_iso):
    """{pays_site: [noms des chefs d'État / de gouvernement]} d'après l'annuaire de la CIA (titres principaux)."""
    base = "https://www.cia.gov/resources/world-leaders/page-data"
    r = requests.get(base + "/sq/d/3338022342.json", headers=UA, timeout=60)
    noms_pays = []
    if r.ok:
        try: noms_pays = [n["country"] for n in r.json()["data"]["leaders"]["nodes"]]
        except Exception: noms_pays = []
    if not noms_pays: noms_pays = list(CIA_ISO)
    res = {}
    for nom_pays in noms_pays:
        pays = pays_depuis_iso(CIA_ISO.get(nom_pays, ""))
        if not pays: continue
        slug = re.sub(r"[^a-z0-9]+", "-", nom_pays.lower().replace(", the", "").replace("'", "")).strip("-")
        try:
            p = requests.get(f"{base}/foreign-governments/{slug}/page-data.json", headers=UA, timeout=30)
            if not p.ok: continue
            page = p.json()["result"]["data"]["page"]
        except Exception:
            continue
        noms = [l["name"] for l in page.get("leaders", [])[:6]
                if l.get("name") and CIA_TITRES.match((l.get("title") or "").strip())]
        if noms: res[pays] = {"noms": noms, "maj": (page.get("date_updated") or "")[:10]}
    return res
CIA_ISO = {
    "Afghanistan": "af", "Albania": "al", "Algeria": "dz", "Andorra": "ad",
    "Angola": "ao", "Antigua and Barbuda": "ag", "Argentina": "ar", "Armenia": "am",
    "Aruba": "aw", "Australia": "au", "Austria": "at", "Azerbaijan": "az",
    "Bahamas, The": "bs", "Bahrain": "bh", "Bangladesh": "bd", "Barbados": "bb",
    "Belarus": "by", "Belgium": "be", "Belize": "bz", "Benin": "bj",
    "Bermuda": "bm", "Bhutan": "bt", "Bolivia": "bo", "Bosnia and Herzegovina": "ba",
    "Botswana": "bw", "Brazil": "br", "Brunei": "bn", "Bulgaria": "bg",
    "Burkina Faso": "bf", "Burma": "mm", "Burundi": "bi", "Cabo Verde": "cv",
    "Cambodia": "kh", "Cameroon": "cm", "Canada": "ca", "Central African Republic": "cf",
    "Chad": "td", "Chile": "cl", "China": "cn", "Colombia": "co",
    "Comoros": "km", "Congo, Democratic Republic of the": "cd", "Congo, Republic of the": "cg", "Cook Islands": "ck",
    "Costa Rica": "cr", "Cote d'Ivoire": "ci", "Croatia": "hr", "Cuba": "cu",
    "Cyprus": "cy", "Czechia": "cz", "Denmark": "dk", "Djibouti": "dj",
    "Dominica": "dm", "Dominican Republic": "do", "Ecuador": "ec", "Egypt": "eg",
    "El Salvador": "sv", "Equatorial Guinea": "gq", "Eritrea": "er", "Estonia": "ee",
    "Eswatini": "sz", "Ethiopia": "et", "Fiji": "fj", "Finland": "fi",
    "France": "fr", "Gabon": "ga", "Gambia, The": "gm", "Georgia": "ge",
    "Germany": "de", "Ghana": "gh", "Greece": "gr", "Grenada": "gd",
    "Guatemala": "gt", "Guinea": "gn", "Guinea-Bissau": "gw", "Guyana": "gy",
    "Haiti": "ht", "Holy See (Vatican City)": "va", "Honduras": "hn", "Hungary": "hu",
    "Iceland": "is", "India": "in", "Indonesia": "id", "Iran": "ir",
    "Iraq": "iq", "Ireland": "ie", "Israel": "il", "Italy": "it",
    "Jamaica": "jm", "Japan": "jp", "Jordan": "jo", "Kazakhstan": "kz",
    "Kenya": "ke", "Kiribati": "ki", "Korea, North": "kp", "Korea, South": "kr",
    "Kosovo": "xk", "Kuwait": "kw", "Kyrgyzstan": "kg", "Laos": "la",
    "Latvia": "lv", "Lebanon": "lb", "Lesotho": "ls", "Liberia": "lr",
    "Libya": "ly", "Liechtenstein": "li", "Lithuania": "lt", "Luxembourg": "lu",
    "Madagascar": "mg", "Malawi": "mw", "Malaysia": "my", "Maldives": "mv",
    "Mali": "ml", "Malta": "mt", "Marshall Islands": "mh", "Mauritania": "mr",
    "Mauritius": "mu", "Mexico": "mx", "Micronesia, Federated States of": "fm", "Moldova": "md",
    "Monaco": "mc", "Mongolia": "mn", "Montenegro": "me", "Morocco": "ma",
    "Mozambique": "mz", "Namibia": "na", "Nauru": "nr", "Nepal": "np",
    "Netherlands": "nl", "New Zealand": "nz", "Nicaragua": "ni", "Niger": "ne",
    "Nigeria": "ng", "Niue": "nu", "North Macedonia": "mk", "Norway": "no",
    "Oman": "om", "Pakistan": "pk", "Palau": "pw", "Panama": "pa",
    "Papua New Guinea": "pg", "Paraguay": "py", "Peru": "pe", "Philippines": "ph",
    "Poland": "pl", "Portugal": "pt", "Qatar": "qa", "Romania": "ro",
    "Russia": "ru", "Rwanda": "rw", "Saint Kitts and Nevis": "kn", "Saint Lucia": "lc",
    "Saint Vincent and the Grenadines": "vc", "Samoa": "ws", "San Marino": "sm", "Sao Tome and Principe": "st",
    "Saudi Arabia": "sa", "Senegal": "sn", "Serbia": "rs", "Seychelles": "sc",
    "Sierra Leone": "sl", "Singapore": "sg", "Slovakia": "sk", "Slovenia": "si",
    "Solomon Islands": "sb", "Somalia": "so", "South Africa": "za", "South Sudan": "ss",
    "Spain": "es", "Sri Lanka": "lk", "Sudan": "sd", "Suriname": "sr",
    "Sweden": "se", "Switzerland": "ch", "Syria": "sy", "Taiwan": "tw",
    "Tajikistan": "tj", "Tanzania": "tz", "Thailand": "th", "Timor-Leste": "tl",
    "Togo": "tg", "Tonga": "to", "Trinidad and Tobago": "tt", "Tunisia": "tn",
    "Turkey": "tr", "Turkmenistan": "tm", "Tuvalu": "tv", "Uganda": "ug",
    "Ukraine": "ua", "United Arab Emirates": "ae", "United Kingdom": "gb", "Uruguay": "uy",
    "Uzbekistan": "uz", "Vanuatu": "vu", "Venezuela": "ve", "Vietnam": "vn",
    "Yemen": "ye", "Zambia": "zm", "Zimbabwe": "zw",
}
