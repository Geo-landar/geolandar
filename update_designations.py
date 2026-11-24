# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Dirigeant désigné, pas encore en fonction — v1.0 (24/11/2026)
#
#  Après une élection législative (ou présidentielle), le futur chef du
#  gouvernement (ou président élu) n'est pas encore en fonction : le site
#  continue d'afficher le sortant. Ce script repère la personne désignée et
#  l'enregistre dans la table `dirigeants` (designe_nom, designe_titre,
#  designe_depuis) ; le site affiche alors « X a été désigné(e) … —
#  formation du gouvernement en cours ».
#
#  Sources : l'encadré de l'article Wikipédia de l'élection, en anglais
#  (champ « after_election ») ET en français (champ « successeur ») — les deux
#  doivent donner la même personne.
#  Règles (décidées avec Maximilien le 24/11/2026) :
#   - mention affichée au plus 2 mois (le site la masque ensuite) ;
#   - si une autre personne est désignée entre-temps, elle remplace la
#     précédente et un nouveau délai de 2 mois démarre ;
#   - la mention est retirée dès que la personne désignée est le dirigeant
#     affiché (prise de fonction confirmée par les sources).
# ══════════════════════════════════════════════════════════════════
import os, re, json, time, requests
from datetime import date, datetime, timedelta
from supabase import create_client
import sources_dirigeants as S

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_KEY else None
ICI = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Geolandar/1.0 (https://geolandar.fr; contact@geolandar.fr)"}
FENETRE = 120        # jours après l'élection pendant lesquels on cherche une désignation
DUREE = 60           # durée maximale d'affichage d'une même désignation (2 mois)

def tables_site():
    """Codes ISO → noms du site, et pays où le site affiche le chef de l'État."""
    src = open(os.path.join(ICI, "update_dirigeants.py"), encoding="utf-8").read()
    env = {}
    exec(src[src.index("ISO_VERS_SITE = {"):src.index("def pays_site")], env)
    env2 = {}
    exec(src[src.index("PAYS_HOS = {"):src.index("}", src.index("PAYS_HOS = {")) + 1], env2)
    inv = {}
    for iso, p in env["ISO_VERS_SITE"].items(): inv.setdefault(p, iso.upper())
    return inv, env2["PAYS_HOS"]

def wikidata(q):
    for essai in range(2):
        try:
            r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"},
                             headers={"Accept": "application/json", **UA}, timeout=120)
            r.raise_for_status(); return r.json()["results"]["bindings"]
        except Exception as e:
            print(f"  Wikidata erreur (essai {essai + 1}) : {type(e).__name__}"); time.sleep(10)
    return []

def articles(elections, iso):
    """(pays, date) → (article anglais, article français) de l'élection."""
    vals = " ".join(f'("{iso[e["pays"]]}" "{e["date"]}"^^xsd:date)' for e in elections if e["pays"] in iso)
    if not vals: return {}
    q = f"""SELECT ?iso ?d ?en ?fr WHERE {{
  VALUES (?iso ?d) {{ {vals} }}
  ?pays wdt:P297 ?iso .
  ?el wdt:P17 ?pays ; wdt:P585 ?t .
  FILTER(xsd:date(?t) = ?d)
  OPTIONAL {{ ?en schema:about ?el ; schema:isPartOf <https://en.wikipedia.org/> . }}
  OPTIONAL {{ ?fr schema:about ?el ; schema:isPartOf <https://fr.wikipedia.org/> . }}
}}"""
    inv = {v: k for k, v in iso.items()}
    titre = lambda u: requests.utils.unquote(u.split("/wiki/")[-1]).replace("_", " ") if u else ""
    res = {}
    for d in wikidata(q):
        cle = (inv.get(d["iso"]["value"]), d["d"]["value"][:10])
        en, fr = titre(d.get("en", {}).get("value", "")), titre(d.get("fr", {}).get("value", ""))
        if en or fr:
            a, b = res.get(cle, ("", ""))
            res[cle] = (a or en, b or fr)
    return res

def encadre(lang, titre):
    r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "parse", "page": titre, "prop": "wikitext", "section": 0, "format": "json", "formatversion": 2, "redirects": 1})
    r.raise_for_status()
    t = r.json().get("parse", {}).get("wikitext", "")
    t = re.sub(r"<ref[^>]*/>", "", t); t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)

def champ(t, nom):
    m = re.search(r"\n\s*\|\s*" + nom + r"\s*=([^\n]*)", t)
    return m.group(1).strip() if m else ""

def personne(valeur):
    """Nom de personne dans un champ (« [[Friedrich Merz]] », « [[Merz cabinet]] », « TBD » → '')."""
    if not valeur or re.search(r"\b(TBD|to be determined|à déterminer|vacant)\b", valeur, re.I): return ""
    m = re.search(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", valeur)
    cible = (m.group(1) if m else re.sub(r"[\[\]{}'|]", "", valeur)).strip()
    aff = (m.group(2) if m and m.group(2) else cible).strip()
    if re.search(r"\b(TBD)\b", aff): return ""
    c = re.match(r"^(.+?) (?:cabinet|government|ministry)$", cible, re.I)     # « Merz cabinet » → Merz
    if c and not re.search(r"\bof\b|\d", c.group(1)): return c.group(1)
    c = re.match(r"^(?:cabinet|gouvernement) (.+)$", cible, re.I)                # « Cabinet Jetten » → Jetten
    if c and not re.search(r"\b(de|du|des|d)\b|\d", c.group(1)): return c.group(1)
    if re.search(r"\b(cabinet|government|ministry|gouvernement|of)\b|\d", cible, re.I): return ""
    return re.sub(r"\s*\([^)]*\)$", "", aff)

def main():
    print("=" * 55)
    print("  GEOLANDAR — Dirigeants désignés v1.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)
    if supabase is None:
        print("  (pas de clé Supabase : rien à faire)"); return
    iso, pays_hos = tables_site()
    debut = (date.today() - timedelta(days=FENETRE)).isoformat()
    try:
        els = supabase.table("elections").select("pays,date,type").eq("niveau", "national") \
            .in_("type", ["l", "p"]).gte("date", debut).lte("date", date.today().isoformat()).execute().data
        dirs = {r["pays"]: r for r in supabase.table("dirigeants").select("*").execute().data}
    except Exception as ex:
        print(f"  ✗ Supabase illisible : {ex}"); return
    # législatives → chef du gouvernement (pays où le site l'affiche) ; présidentielles → président élu
    utiles = [e for e in els if "-00" not in e["date"] and
              ((e["type"] == "l" and e["pays"] not in pays_hos) or (e["type"] == "p" and e["pays"] in pays_hos))]
    print(f"  {len(utiles)} élection(s) récente(s) à surveiller")
    arts = articles(utiles, iso)
    vus, ecrits, retires = set(), [], []
    for e in sorted(utiles, key=lambda x: x["date"], reverse=True):
        p = e["pays"]
        if p in vus or p not in dirs: continue
        vus.add(p)
        en, fr = arts.get((p, e["date"]), ("", ""))
        if not (en and fr):
            print(f"  · {p} ({e['date']}) : article Wikipédia {'anglais' if not en else 'français'} introuvable"); continue
        try:
            t_en, t_fr = encadre("en", en), encadre("fr", fr)
        except Exception as ex:
            print(f"  ✗ {p} : {type(ex).__name__}"); continue
        n_en, n_fr = personne(champ(t_en, "after_election")), personne(champ(t_fr, "successeur"))
        poste = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", champ(t_fr, "poste")).strip()
        d = dirs[p]
        actuel = d.get("nom") or ""
        designe = max(n_en, n_fr, key=len) if (n_en and n_fr and S.meme_personne(n_en, n_fr)) else ""
        if designe and len(designe.split()) == 1:            # nom seul : nom complet pris parmi les têtes de liste
            for m in re.finditer(r"\n\s*\|\s*(?:leader|chef)\d*\s*=\s*\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", t_en + t_fr):
                plein = re.sub(r"\s*\([^)]*\)$", "", (m.group(2) or m.group(1)).strip())
                if S.meme_personne(plein, designe) and len(plein.split()) > 1:
                    designe = plein; break
        if designe and S.meme_personne(designe, actuel):
            designe = ""                                       # déjà en fonction (ou reconduit)
        if designe:
            if d.get("designe_nom") and S.meme_personne(d["designe_nom"], designe):
                continue                                       # même désignation : on garde la date d'origine
            titre = poste if poste and not re.search(r"cabinet|gouvernement", poste, re.I) else (d.get("titre") or "")
            supabase.table("dirigeants").update({"designe_nom": designe, "designe_titre": titre,
                                                 "designe_depuis": date.today().isoformat()}).eq("pays", p).execute()
            ecrits.append(f"{p} : {designe} désigné(e) {titre.lower()} (sortant : {actuel})")
        elif d.get("designe_nom") and (not n_en or S.meme_personne(d["designe_nom"], actuel)):
            supabase.table("dirigeants").update({"designe_nom": None, "designe_titre": None, "designe_depuis": None}).eq("pays", p).execute()
            retires.append(f"{p} : {d['designe_nom']} (en fonction ou plus désigné)")
    # désignations des pays sans élection récente : retirées si la personne est entrée en fonction
    for p, d in dirs.items():
        if p not in vus and d.get("designe_nom") and S.meme_personne(d["designe_nom"], d.get("nom")):
            supabase.table("dirigeants").update({"designe_nom": None, "designe_titre": None, "designe_depuis": None}).eq("pays", p).execute()
            retires.append(f"{p} : {d['designe_nom']} (entré(e) en fonction)")
    print(f"  ✓ {len(ecrits)} désignation(s) enregistrée(s)")
    for x in ecrits: print(f"     - {x}")
    print(f"  ✓ {len(retires)} désignation(s) retirée(s)")
    for x in retires: print(f"     - {x}")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        if "designe_" in str(ex):
            print("  ✗ Colonnes designe_* absentes : exécuter geolandar_designations.sql dans Supabase (SQL Editor).")
        else:
            raise
