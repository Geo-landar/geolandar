# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Dirigeants régionaux et composition des chambres — v1.0 (13/11/2026)
#
#  Chaque nuit :
#   1. Remplit Supabase (tables dirigeants_regionaux et chambres_composition)
#      à partir des données vérifiées du site (data/regions_chambres.json,
#      exporté de la version de test par tools/export_regions_chambres.js).
#      Une ligne déjà mise à jour par l'automatisation n'est pas écrasée,
#      sauf si le fichier a été vérifié plus récemment.
#   2. Dirigeants régionaux : compare avec Wikidata (chef de l'exécutif
#      de chaque région, P6). Un nouveau nom n'est écrit QUE si Wikidata
#      indique une prise de fonction postérieure à notre dernière
#      vérification (sinon c'est probablement Wikidata qui est en retard :
#      simple signalement « à vérifier » dans le journal).
#   3. Chambres : après des législatives (ou sénatoriales) tenues depuis la
#      dernière vérification, la chambre est marquée « renouvellement en
#      cours » (perime) — le site l'indique — et listée dans le journal
#      pour mise à jour de la répartition des sièges.
# ══════════════════════════════════════════════════════════════════
import json, os, re, time, unicodedata
from datetime import date, datetime
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_KEY else None
ICI = os.path.dirname(os.path.abspath(__file__))
AUJ = date.today().isoformat()
VERIF_MIN = "2026-09-01"     # les données du site ont été vérifiées en septembre-novembre 2026

# Pays non comparés à Wikidata (exécutif collégial, titres non personnels, ou
# Wikidata non fiable pour ce pays) : leurs lignes restent celles du fichier.
SANS_WIKIDATA = {"Suisse", "Pays-Bas", "Bosnie", "Chine", "Emirats arabes"}

MOIS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
        "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12}

def date_fr(s):
    """« 11 octobre 2026 » → « 2026-10-11 » (au plus tôt VERIF_MIN)."""
    m = re.search(r"(\d{1,2})(?:er)?\s+(\S+)\s+(20\d\d)", s or "")
    iso = ""
    if m and m.group(2).lower() in MOIS:
        iso = f"{m.group(3)}-{MOIS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return max(iso, VERIF_MIN) if iso else VERIF_MIN

def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip()

VIDES = {"bin", "ben", "ibn", "al", "el", "de", "da", "du", "von", "van", "der", "prince", "roi", "sheikh", "cheikh",
         "abdel", "abdul", "mohammed", "muhammad", "mohamed", "ahmed", "ali", "jean", "jr"}

def meme_personne(a, b):
    """Même règle que le site (memePersonneNoms)."""
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

def norm_region(s):
    """Nom de région comparable : sans accents, sans mots génériques."""
    t = norm(s)
    t = re.sub(r"\b(region|province|etat|state|oblast|prefecture|departement|governorate|gouvernorat|wilaya|"
               r"county|canton|land|republique|republic|of|de|du|des|la|le|les|d|l|kraj|voivodeship|voivodie|"
               r"autonomous community|communaute autonome|federal subject|territory|territoire)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# ── Codes ISO des pays du site (même table que update_elections.py)
def iso_des_pays():
    src = open(os.path.join(ICI, "update_elections.py"), encoding="utf-8").read()
    bloc = src[src.index("ISO_VERS_SITE = {"):src.index("NOMS_SITE")]
    env = {}; exec(bloc, env)
    inv = {}
    for iso, p in env["ISO_VERS_SITE"].items(): inv.setdefault(p, iso.upper())
    return inv

def wikidata(query, label):
    for essai in range(2):
        try:
            r = requests.get("https://query.wikidata.org/sparql", params={"query": query, "format": "json"},
                             headers={"Accept": "application/json", "User-Agent": "Geolandar/1.0 (geolandar.fr)"}, timeout=120)
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:
            print(f"  Wikidata erreur {label} (essai {essai + 1}) : {type(e).__name__}")
            time.sleep(10)
    return None

def requete_regions(isos):
    vals = " ".join(f'"{i}"' for i in isos)
    return f"""
SELECT ?iso ?reg ?regFr ?regEn ?regAlt ?pers ?persFr ?persEn ?debut ?partiFr ?partiEn WHERE {{
  VALUES ?iso {{ {vals} }}
  ?pays wdt:P297 ?iso .
  {{ ?pays wdt:P150 ?reg . }} UNION {{ ?reg wdt:P131 ?pays . ?reg wdt:P31/wdt:P279* wd:Q10864048 . }}
  ?reg p:P6 ?st . ?st ps:P6 ?pers . ?st wikibase:rank ?rang .
  FILTER(?rang != wikibase:DeprecatedRank)
  FILTER NOT EXISTS {{ ?st pq:P582 ?fin . }}
  FILTER NOT EXISTS {{ ?reg wdt:P576 ?dissous . }}
  OPTIONAL {{ ?st pq:P580 ?debut . }}
  OPTIONAL {{ ?reg rdfs:label ?regFr . FILTER(LANG(?regFr) = "fr") }}
  OPTIONAL {{ ?reg rdfs:label ?regEn . FILTER(LANG(?regEn) = "en") }}
  OPTIONAL {{ ?reg skos:altLabel ?regAlt . FILTER(LANG(?regAlt) IN ("fr", "en")) }}
  OPTIONAL {{ ?pers rdfs:label ?persFr . FILTER(LANG(?persFr) = "fr") }}
  OPTIONAL {{ ?pers rdfs:label ?persEn . FILTER(LANG(?persEn) = "en") }}
  OPTIONAL {{ ?pers p:P102 ?pst . ?pst ps:P102 ?parti . FILTER NOT EXISTS {{ ?pst pq:P582 ?pfin . }}
             OPTIONAL {{ ?parti rdfs:label ?partiFr . FILTER(LANG(?partiFr) = "fr") }}
             OPTIONAL {{ ?parti rdfs:label ?partiEn . FILTER(LANG(?partiEn) = "en") }} }}
}}"""

def val(row, k): return row.get(k, {}).get("value", "")

# ══════════════════════════════════════
# 1. Remplissage depuis le fichier du site
# ══════════════════════════════════════
def lire_table(table, cols):
    rows, debut = [], 0
    while True:
        lot = supabase.table(table).select(cols).range(debut, debut + 999).execute().data
        rows += lot
        if len(lot) < 1000: return rows
        debut += 1000

def remplir(table, lignes, cols_cle, champs):
    cle = lambda r: tuple(r[c] for c in cols_cle)
    try:
        existants = {cle(r): r for r in lire_table(table, "*")}
    except Exception as ex:
        print(f"  ✗ table {table} illisible ({ex}). Le fichier SQL geolandar_regions_chambres_tables.sql a-t-il été exécuté ?")
        return None
    a_ecrire = []
    for l in lignes:
        e = existants.get(cle(l))
        if e and e.get("source") == "wikidata" and date_fr(l.get("verifie")) <= (e.get("verifie") or ""):
            continue                                    # mise à jour automatique plus récente : on garde
        nouveau = {k: l.get(k) for k in champs}
        nouveau.update({"source": "fichier", "verifie": date_fr(l.get("verifie")), "updated_at": datetime.now().isoformat()})
        if e and e.get("perime") and "perime" in nouveau and nouveau["verifie"] <= (e.get("verifie") or ""):
            nouveau["perime"] = True                    # renouvellement signalé par l'automatisation : on garde
        if e and all(e.get(k) == nouveau[k] for k in champs + ["verifie"]):
            continue                                    # déjà identique
        a_ecrire.append(nouveau)
    for i in range(0, len(a_ecrire), 200):
        supabase.table(table).upsert(a_ecrire[i:i + 200], on_conflict=",".join(cols_cle)).execute()
    print(f"  {table} : {len(a_ecrire)} ligne(s) écrite(s) depuis le fichier, {len(existants)} déjà présentes")
    return lire_table(table, "*")


# ══════════════════════════════════════
# 2. Dirigeants régionaux ↔ Wikidata
# ══════════════════════════════════════
def verifier_dirigeants(rows):
    iso = iso_des_pays()
    par_pays = {}
    for r in rows:
        if r["pays"] in SANS_WIKIDATA or r.get("college"): continue
        par_pays.setdefault(r["pays"], []).append(r)
    pays = sorted(p for p in par_pays if p in iso)
    ecrits, a_verifier, sans_corresp, vus = [], [], 0, 0
    for i in range(0, len(pays), 6):
        lot = pays[i:i + 6]
        data = wikidata(requete_regions([iso[p] for p in lot]), ", ".join(lot))
        time.sleep(2)
        if data is None: continue
        # région Wikidata → titulaires actuels
        regs = {}
        for d in data:
            q = val(d, "reg")
            g = regs.setdefault(q, {"iso": val(d, "iso"), "noms": set(), "pers": {}})
            for k in ("regFr", "regEn", "regAlt"):
                if val(d, k): g["noms"].add(norm_region(val(d, k)))
            p = g["pers"].setdefault(val(d, "pers"), {"nom": val(d, "persFr") or val(d, "persEn"), "debut": "", "partis": set()})
            if val(d, "debut"): p["debut"] = max(p["debut"], val(d, "debut")[:10])
            if val(d, "partiFr") or val(d, "partiEn"): p["partis"].add(val(d, "partiFr") or val(d, "partiEn"))
        for p in lot:
            for r in par_pays[p]:
                cible = norm_region(r["region"])
                cand = [g for g in regs.values() if g["iso"] == iso[p] and cible and cible in g["noms"]]
                if len(cand) != 1:
                    sans_corresp += 1; continue
                vus += 1
                titulaires = [t for t in cand[0]["pers"].values() if t["nom"] and not re.match(r"^Q\d+$", t["nom"])]
                if len(titulaires) != 1 or meme_personne(titulaires[0]["nom"], r.get("nom")):
                    continue
                t = titulaires[0]
                if t["debut"] and t["debut"] > (r.get("verifie") or VERIF_MIN):
                    parti = sorted(t["partis"])[0] if len(t["partis"]) == 1 else ""
                    supabase.table("dirigeants_regionaux").update({
                        "nom": t["nom"], "parti": parti, "pos": None, "source": "wikidata",
                        "verifie": AUJ, "updated_at": datetime.now().isoformat()
                    }).eq("pays", p).eq("region", r["region"]).execute()
                    ecrits.append(f"{p} / {r['region']} : {r.get('nom')} → {t['nom']} (en fonction depuis le {t['debut']})")
                else:
                    a_verifier.append(f"{p} / {r['region']} : site {r.get('nom')!r}, Wikidata {t['nom']!r}"
                                      + (f" (depuis le {t['debut']})" if t["debut"] else " (sans date)"))
    print(f"  {vus} régions comparées à Wikidata ({sans_corresp} sans correspondance de nom, laissées telles quelles)")
    for e in ecrits: print(f"  ✓ {e}")
    if a_verifier:
        print(f"\n  📋 {len(a_verifier)} région(s) où Wikidata diffère sans changement récent (site conservé) :")
        for e in a_verifier: print(f"     - {e}")

# ══════════════════════════════════════
# 3. Chambres : renouvellement après une élection
# ══════════════════════════════════════
def marquer_chambres(rows):
    try:
        el = supabase.table("elections").select("pays,date,type").eq("niveau", "national").in_("type", ["l", "s"]).lte("date", AUJ).execute().data
    except Exception as ex:
        print(f"  ✗ élections illisibles : {ex}"); return
    par_pays = {}
    for r in rows: par_pays.setdefault(r["pays"], []).append(r)
    marques = []
    for e in el:
        chs = sorted(par_pays.get(e["pays"], []), key=lambda r: r.get("ordre") or 0)
        if not chs or "-00" in e["date"]: continue
        ch = chs[0] if e["type"] == "l" else (chs[1] if len(chs) > 1 else None)
        if not ch or ch.get("perime") or e["date"] <= (ch.get("verifie") or VERIF_MIN): continue
        supabase.table("chambres_composition").update({"perime": True, "updated_at": datetime.now().isoformat()}).eq("id", ch["id"]).execute()
        ch["perime"] = True
        marques.append(f"{e['pays']} / {ch['chambre']} (élection du {e['date']})")
    print(f"  {len(marques)} chambre(s) marquée(s) « renouvellement en cours »")
    for m in marques: print(f"     ⚠ {m}")
    restantes = [f"{r['pays']} / {r['chambre']}" for r in rows if r.get("perime")]
    if restantes:
        print(f"  📋 {len(restantes)} chambre(s) à mettre à jour (répartition des sièges) : {', '.join(restantes)}")

def main():
    print("=" * 55)
    print("  GEOLANDAR — Régions et chambres v1.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)
    if supabase is None:
        print("  (pas de clé Supabase : rien à faire)"); return
    donnees = json.load(open(os.path.join(ICI, "data", "regions_chambres.json"), encoding="utf-8"))
    print("\n[1] Remplissage depuis les données du site...")
    dirs = remplir("dirigeants_regionaux", donnees["dirigeants"], ("pays", "region"), ["pays", "region", "nom", "titre", "parti", "pos", "college"])
    chs = remplir("chambres_composition", donnees["chambres"], ("pays", "chambre"), ["pays", "chambre", "total", "groupes", "perime", "ordre"])
    if dirs:
        print("\n[2] Dirigeants régionaux : comparaison avec Wikidata...")
        verifier_dirigeants(dirs)
    if chs:
        print("\n[3] Chambres : élections tenues depuis la dernière vérification...")
        marquer_chambres(chs)
    print(f"\n  Terminé : {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
