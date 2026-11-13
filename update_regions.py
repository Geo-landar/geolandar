# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Dirigeants régionaux et composition des chambres — v2.0 (13/11/2026)
#  v2.0 : plusieurs sources. Dirigeants régionaux : Wikidata + listes Wikipédia
#  des dirigeants en fonction + encadré de l'article de chaque région (2 sources
#  d'accord et une date récente pour écrire). Chambres : Wikipédia en + Wikipédia
#  fr + sources officielles (Royaume-Uni, Assemblée nationale) ; 2 sources
#  d'accord pour écrire après une élection, source officielle seule en continu.
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
from datetime import date, datetime, timedelta
import requests
from supabase import create_client
import chambres_wiki as CW
import sources_regions as SR

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_KEY else None
ICI = os.path.dirname(os.path.abspath(__file__))
AUJ = date.today().isoformat()
VERIF_MIN = "2026-09-01"     # les données du site ont été vérifiées en septembre-novembre 2026

# Pays non comparés à Wikidata (exécutif collégial, titres non personnels, ou
# Wikidata non fiable pour ce pays) : leurs lignes restent celles du fichier.
SANS_WIKIDATA = {"Suisse", "Pays-Bas", "Bosnie", "Chine", "Emirats arabes"}

# Lignes écrites à tort par l'automatisation, remises à la valeur du fichier
# (pays, chambre, date de l'écriture fautive) — sans effet ensuite.
REINITIALISER = {("Nouvelle-Zelande", "Chambre des représentants", "2026-11-13")}

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
SELECT ?iso ?reg ?regFr ?regEn ?regAlt ?article ?pers ?persFr ?persEn ?debut ?partiFr ?partiEn WHERE {{
  VALUES ?iso {{ {vals} }}
  ?pays wdt:P297 ?iso .
  {{ ?pays wdt:P150 ?reg . }} UNION {{ ?reg wdt:P131 ?pays . ?reg wdt:P31/wdt:P279* wd:Q10864048 . }}
  FILTER NOT EXISTS {{ ?reg wdt:P576 ?dissous . }}
  OPTIONAL {{ ?article schema:about ?reg ; schema:isPartOf <https://en.wikipedia.org/> . }}
  OPTIONAL {{ ?reg p:P6 ?st . ?st ps:P6 ?pers . ?st wikibase:rank ?rang .
             FILTER(?rang != wikibase:DeprecatedRank)
             FILTER NOT EXISTS {{ ?st pq:P582 ?fin . }}
             OPTIONAL {{ ?st pq:P580 ?debut . }} }}
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
        if e and (e.get("pays"), e.get("chambre"), e.get("verifie")) in REINITIALISER:
            e = dict(e, source="fichier")                   # mise à jour automatique erronée : on repart du fichier
        if e and e.get("source") not in (None, "", "fichier") and date_fr(l.get("verifie")) <= (e.get("verifie") or ""):
            continue                                    # mise à jour automatique plus récente : on garde
        nouveau = {k: l.get(k) for k in champs}
        nouveau.update({"source": "fichier", "verifie": date_fr(l.get("verifie")), "updated_at": datetime.now().isoformat()})
        if e and "perime" in nouveau:
            nouveau["perime"] = e.get("perime")         # géré par l'étape 3 (renouvellement)
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
    """Compare chaque dirigeant régional avec 3 sources : Wikidata, la liste
    Wikipédia des dirigeants en fonction du pays (avec date) et l'encadré de
    l'article de la région. Un nouveau nom est écrit s'il est donné par au
    moins 2 sources ET daté d'après notre dernière vérification."""
    iso = iso_des_pays()
    par_pays = {}
    for r in rows:
        if r["pays"] in SANS_WIKIDATA or r.get("college"): continue
        par_pays.setdefault(r["pays"], []).append(r)
    pays = sorted(p for p in par_pays if p in iso)
    infos = {}                      # (pays, région) → {"wd": [...], "article": str, "alias": set}
    for i in range(0, len(pays), 6):
        lot = pays[i:i + 6]
        data = wikidata(requete_regions([iso[p] for p in lot]), ", ".join(lot))
        time.sleep(2)
        if data is None: continue
        regs = {}
        for d in data:
            g = regs.setdefault(val(d, "reg"), {"iso": val(d, "iso"), "noms": set(), "pers": {}, "article": ""})
            for k in ("regFr", "regEn", "regAlt"):
                if val(d, k): g["noms"].add(norm_region(val(d, k)))
            if val(d, "article"):
                g["article"] = requests.utils.unquote(val(d, "article").split("/wiki/")[-1]).replace("_", " ")
            if not val(d, "pers"): continue
            p = g["pers"].setdefault(val(d, "pers"), {"nom": val(d, "persFr") or val(d, "persEn"), "debut": "", "partis": set()})
            if val(d, "debut"): p["debut"] = max(p["debut"], val(d, "debut")[:10])
            if val(d, "partiFr") or val(d, "partiEn"): p["partis"].add(val(d, "partiFr") or val(d, "partiEn"))
        for p in lot:
            for r in par_pays[p]:
                cible = norm_region(r["region"])
                cand = [g for g in regs.values() if g["iso"] == iso[p] and cible and cible in g["noms"]]
                if len(cand) != 1: continue
                g = cand[0]
                alias = set(g["noms"]) | ({norm_region(re.sub(r"\s*\([^)]*\)$", "", g["article"]))} if g["article"] else set())
                infos[(p, r["region"])] = {"wd": [t for t in g["pers"].values() if t["nom"] and not re.match(r"^Q\d+$", t["nom"])],
                                           "article": g["article"], "alias": alias}
    # Source 2 : encadrés des articles des régions (50 par appel)
    encadres = SR.lire_infobox([x["article"] for x in infos.values() if x["article"]])
    # Source 3 : listes des dirigeants en fonction
    listes = {}
    for p, titre in SR.LISTES.items():
        if p not in par_pays: continue
        alias = {}
        for r in par_pays[p]:
            alias[norm_region(r["region"])] = r["region"]
            for a in infos.get((p, r["region"]), {}).get("alias", ()):
                alias.setdefault(a, r["region"])
        try:
            listes[p] = SR.lire_liste(titre, alias, lambda x: norm_region(x))
        except Exception as ex:
            print(f"  ✗ liste {p} indisponible ({type(ex).__name__})")
        time.sleep(1)
    print(f"  Sources : Wikidata {len(infos)} régions reconnues, encadrés {len(encadres)} articles, "
          f"listes {sum(len(v) for v in listes.values())} régions ({len(listes)} pays)")

    ecrits, a_verifier, confirmes = [], [], 0
    for p in pays:
        for r in par_pays[p]:
            info = infos.get((p, r["region"]), {})
            wd = info.get("wd", [])
            sources = {}
            if len(wd) == 1: sources["Wikidata"] = (wd[0]["nom"], wd[0]["debut"])
            if (p in listes) and r["region"] in listes[p]: sources["liste Wikipédia"] = listes[p][r["region"]]
            noms_enc = encadres.get(info.get("article", ""), [])
            if noms_enc: sources["article Wikipédia"] = (noms_enc[0], "")
            actuel = r.get("nom") or ""
            if not sources: continue
            if any(meme_personne(n, actuel) for n, _ in sources.values()) or any(meme_personne(n, actuel) for n in noms_enc):
                confirmes += 1; continue
            # candidats : chaque nom proposé, avec les sources qui le donnent
            meilleur = None
            for nom, _ in sources.values():
                accord = [k for k, (n, _) in sources.items() if meme_personne(n, nom)]
                if "article Wikipédia" not in accord and any(meme_personne(nom, n) for n in noms_enc): accord.append("article Wikipédia")
                date_c = max([d for k, (n, d) in sources.items() if k in accord and d] or [""])
                if not meilleur or len(accord) > len(meilleur[1]): meilleur = (nom, accord, date_c)
            nom, accord, date_c = meilleur
            nom_fr = next((n for k, (n, _) in sources.items() if k == "Wikidata" and meme_personne(n, nom)), nom)
            if len(accord) >= 2 and date_c and date_c > (r.get("verifie") or VERIF_MIN):
                t = wd[0] if (wd and meme_personne(wd[0]["nom"], nom)) else {"partis": set()}
                parti = sorted(t["partis"])[0] if len(t.get("partis", ())) == 1 else ""
                supabase.table("dirigeants_regionaux").update({
                    "nom": nom_fr, "parti": parti, "pos": None, "source": "+".join(accord),
                    "verifie": AUJ, "updated_at": datetime.now().isoformat()
                }).eq("pays", p).eq("region", r["region"]).execute()
                ecrits.append(f"{p} / {r['region']} : {actuel} → {nom_fr} (depuis le {date_c} ; {', '.join(accord)})")
            else:
                raison = "une seule source" if len(accord) < 2 else ("sans date" if not date_c else "prise de fonction antérieure à notre vérification")
                a_verifier.append(f"{p} / {r['region']} : site {actuel!r}, proposé {nom!r} ({', '.join(accord)} ; {raison})")
    print(f"  {confirmes} dirigeant(s) régional(aux) confirmé(s) par au moins une source")
    print(f"  ✓ {len(ecrits)} remplacé(s) :")
    for e in ecrits: print(f"     - {e}")
    if a_verifier:
        print(f"\n  📋 {len(a_verifier)} désaccord(s) non tranché(s), site conservé :")
        for e in a_verifier: print(f"     - {e}")

# ══════════════════════════════════════
# 3. Chambres : renouvellement après une élection
# ══════════════════════════════════════
def marquer_chambres(rows, fichier):
    """perime = vrai si le fichier le dit, ou si une élection a eu lieu depuis la vérification."""
    perime_fichier = {(c["pays"], c["chambre"]): bool(c.get("perime")) for c in fichier}
    try:
        el = supabase.table("elections").select("pays,date,type").eq("niveau", "national").in_("type", ["l", "s"]).lte("date", AUJ).execute().data
    except Exception as ex:
        print(f"  ✗ élections illisibles : {ex}"); return
    par_pays = {}
    for r in rows: par_pays.setdefault(r["pays"], []).append(r)
    marques, elues = [], {}
    for e in el:
        chs = sorted(par_pays.get(e["pays"], []), key=lambda r: r.get("ordre") or 0)
        if not chs or "-00" in e["date"]: continue
        ch = chs[0] if e["type"] == "l" else (chs[1] if len(chs) > 1 else None)
        if ch: ch["_elec"] = max(ch.get("_elec", ""), e["date"])
        if not ch or e["date"] <= (ch.get("verifie") or VERIF_MIN): continue
        if ch["id"] not in elues: marques.append(f"{e['pays']} / {ch['chambre']} (élection du {e['date']})")
        elues[ch["id"]] = max(elues.get(ch["id"], ""), e["date"])
    n = 0
    for ch in rows:
        cible = perime_fichier.get((ch["pays"], ch["chambre"]), False) or ch["id"] in elues
        if bool(ch.get("perime")) != cible:
            supabase.table("chambres_composition").update({"perime": cible, "updated_at": datetime.now().isoformat()}).eq("id", ch["id"]).execute()
            ch["perime"] = cible; n += 1
    print(f"  {len(marques)} chambre(s) renouvelée(s) depuis la dernière vérification ({n} changement(s) écrit(s))")
    for m in marques: print(f"     ⚠ {m}")
    return elues

# ══════════════════════════════════════
# 4. Chambres renouvelées : nouvelle répartition des sièges (Wikipédia en)
#    Écrite seulement si l'infobox indique l'élection attendue (ou plus
#    récente) et si la somme des sièges est cohérente. Les noms et couleurs
#    déjà utilisés sur le site sont gardés pour les groupes reconnus.
# ══════════════════════════════════════
def articles_chambres(isos):
    """{iso: [(article anglais, article français)]} pour chaque chambre (Wikidata P194 et ses parties)."""
    vals = " ".join(f'"{i}"' for i in isos)
    q = f"""SELECT ?iso ?leg ?en ?fr WHERE {{
  VALUES ?iso {{ {vals} }}
  ?pays wdt:P297 ?iso .
  {{ ?pays wdt:P194 ?leg . }} UNION {{ ?pays wdt:P194 ?l0 . ?l0 wdt:P527 ?leg . }}
  OPTIONAL {{ ?en schema:about ?leg ; schema:isPartOf <https://en.wikipedia.org/> . }}
  OPTIONAL {{ ?fr schema:about ?leg ; schema:isPartOf <https://fr.wikipedia.org/> . }}
}}"""
    titre = lambda u: requests.utils.unquote(u.split("/wiki/")[-1]).replace("_", " ") if u else ""
    res = {}
    for d in wikidata(q, "articles des chambres") or []:
        res.setdefault(val(d, "iso"), {})[val(d, "leg")] = (titre(val(d, "en")), titre(val(d, "fr")))
    return {k: sorted(v.values()) for k, v in res.items()}

def construire_groupes(groupes, anciens, teintes):
    """Garde le nom et la couleur du site pour un groupe reconnu (sigle ou nom), sinon ceux de la source."""
    nouveaux, pris = [], set()
    for g in groupes:
        ancien = None
        for k, a in enumerate(anciens):
            if k in pris: continue
            if (g["sigle"] and re.search(r"\b" + re.escape(norm(g["sigle"])) + r"\b", norm(a["n"]))) \
               or meme_personne(a["n"], g["lien"]):
                ancien = k; break
        if ancien is not None:
            pris.add(ancien)
            nouveaux.append({"n": anciens[ancien]["n"], "s": g["s"], "c": anciens[ancien]["c"], "_o": ancien})
        else:
            nom = g["lien"] + (f" ({g['sigle']})" if g["sigle"] and norm(g["sigle"]) not in norm(g["lien"]) else "")
            nouveaux.append({"n": nom, "s": g["s"], "c": teintes.get(g["couleur"], g["couleur"] if g["couleur"].startswith("#") else "#94a3b8"), "_o": 999})
    nouveaux.sort(key=lambda g: g["_o"])
    for g in nouveaux: g.pop("_o")
    return nouveaux

def sieges(groupes): return sorted(g["s"] for g in groupes)

def ecrire_chambre(ch, groupes, source):
    supabase.table("chambres_composition").update({
        "total": sum(g["s"] for g in groupes), "groupes": groupes, "perime": False, "verifie": AUJ,
        "source": source, "updated_at": datetime.now().isoformat()}).eq("id", ch["id"]).execute()
    ch["groupes"], ch["total"], ch["perime"], ch["verifie"], ch["source"] = groupes, sum(g["s"] for g in groupes), False, AUJ, source

def maj_officielles(rows):
    """Chambres disposant d'une source officielle : mises à jour en continu."""
    for ch in rows:
        f = CW.OFFICIELS.get((ch["pays"], ch["chambre"]))
        if not f: continue
        try:
            groupes = f()
        except Exception as ex:
            print(f"  ✗ {ch['pays']} / {ch['chambre']} : source officielle indisponible ({type(ex).__name__})"); continue
        total = sum(g["s"] for g in groupes)
        if not groupes or abs(total - (ch.get("total") or total)) > 5:
            print(f"  ⚠ {ch['pays']} / {ch['chambre']} : réponse officielle incohérente ({total} sièges), ignorée"); continue
        if sieges(groupes) == sieges(ch.get("groupes") or []):
            print(f"  = {ch['pays']} / {ch['chambre']} : inchangée (source officielle)"); continue
        ecrire_chambre(ch, construire_groupes(groupes, ch.get("groupes") or [], {}), "officiel")
        print(f"  ✓ {ch['pays']} / {ch['chambre']} : {total} sièges, {len(groupes)} groupes (source officielle)")

def actualiser_chambres(rows, elues):
    """Chambre renouvelée : nouvelle répartition écrite seulement si 2 sources donnent
    les mêmes sièges (Wikipédia en, Wikipédia fr, source officielle)."""
    limite = (date.today() - timedelta(days=35)).isoformat()
    for r in rows:   # résultats provisoires → définitifs : on revérifie 35 jours
        if r["id"] not in elues and r.get("source") in ("wikipedia", "wikipedia+fr", "wikipedia+officiel") and r.get("_elec", "") >= limite:
            elues[r["id"]] = r["_elec"]
    cibles = [r for r in rows if r["id"] in elues]
    if not cibles:
        print("  aucune chambre renouvelée en attente"); return
    iso = iso_des_pays()
    articles = articles_chambres(sorted({iso[r["pays"]] for r in cibles if r["pays"] in iso}))
    faites, attente = [], []
    for ch in cibles:
        anciens = ch.get("groupes") or []
        trouve = None
        for en, fr in articles.get(iso.get(ch["pays"], ""), []):
            g_en, g_fr = [], []
            try:
                if en:
                    derniere, g_en, total_ib = CW.lire_infobox(en)
                    somme = sum(g["s"] for g in g_en)
                    if derniere < elues[ch["id"]] or not (somme == ch["total"] or (total_ib and somme == total_ib)): g_en = []
                if fr:
                    _, g_fr = CW.lire_infobox_fr(fr)
            except Exception:
                pass
            if not g_en or sieges(g_en) == sieges(anciens): continue      # pas encore à jour
            confirme = []
            if g_fr and sieges(g_fr) == sieges(g_en): confirme.append("Wikipédia fr")
            off = CW.OFFICIELS.get((ch["pays"], ch["chambre"]))
            if off:
                try:
                    if sieges(off()) == sieges(g_en): confirme.append("source officielle")
                except Exception: pass
            if confirme:
                trouve = (en, fr, g_en, g_fr if "Wikipédia fr" in confirme else [], confirme); break
        if not trouve:
            attente.append(f"{ch['pays']} / {ch['chambre']}"); continue
        en, fr, g_en, g_fr, confirme = trouve
        if g_fr:   # noms français
            nouveaux = construire_groupes(g_fr, anciens, CW.couleurs_fr([g["couleur"] for g in g_fr]))
        else:
            nouveaux = construire_groupes(g_en, anciens, CW.couleurs([g["couleur"] for g in g_en]))
        ecrire_chambre(ch, nouveaux, "wikipedia+fr" if g_fr else "wikipedia+officiel")
        faites.append(f"{ch['pays']} / {ch['chambre']} : {ch['total']} sièges, {len(nouveaux)} groupes (Wikipédia en « {en} », confirmé par {', '.join(confirme)})")
    print(f"  ✓ {len(faites)} chambre(s) mise(s) à jour automatiquement")
    for x in faites: print(f"     - {x}")
    if attente:
        print(f"  ⏳ {len(attente)} chambre(s) en attente (sources pas encore à jour ou pas d'accord) : {', '.join(attente)}")

def main():
    print("=" * 55)
    print("  GEOLANDAR — Régions et chambres v2.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)
    if supabase is None:
        print("  (pas de clé Supabase : rien à faire)"); return
    donnees = json.load(open(os.path.join(ICI, "data", "regions_chambres.json"), encoding="utf-8"))
    print("\n[1] Remplissage depuis les données du site...")
    dirs = remplir("dirigeants_regionaux", donnees["dirigeants"], ("pays", "region"), ["pays", "region", "nom", "titre", "parti", "pos", "college"])
    chs = remplir("chambres_composition", donnees["chambres"], ("pays", "chambre"), ["pays", "chambre", "total", "groupes", "perime", "ordre"])
    if dirs:
        print("\n[2] Dirigeants régionaux : comparaison avec Wikidata, les listes et les articles Wikipédia...")
        verifier_dirigeants(dirs)
    if chs:
        print("\n[3] Chambres : élections tenues depuis la dernière vérification...")
        elues = marquer_chambres(chs, donnees["chambres"]) or {}
        print("\n[4] Chambres renouvelées : nouvelle répartition des sièges...")
        actualiser_chambres(chs, elues)
        print("\n[5] Chambres avec source officielle (Royaume-Uni, France)...")
        maj_officielles(chs)
    print(f"\n  Terminé : {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
