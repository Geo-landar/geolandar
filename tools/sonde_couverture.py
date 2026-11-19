# Diagnostic temporaire : couverture des sources des chambres (aucune écriture)
import json, os, sys, time, io, zipfile, requests
sys.path.insert(0, ".")
os.environ["SUPABASE_KEY"] = ""
import update_regions as U, chambres_wiki as CW
UA = CW.UA
def proche(a, b, tol_total=3, tol=2):
    if not a or not b: return False
    if abs(sum(a) - sum(b)) > tol_total: return False
    A, B = sorted(a, reverse=True)[:3], sorted(b, reverse=True)[:3]
    return len(A) == len(B) and all(abs(x - y) <= tol for x, y in zip(A, B))
d = json.load(open("data/regions_chambres.json"))
iso = U.iso_des_pays()
chs = d["chambres"]
MANUEL = {("Pays-Bas", "Tweede Kamer"): ("House of Representatives (Netherlands)", "Seconde Chambre des États généraux"),
          ("Bielorussie", "Chambre des représentants"): ("House of Representatives (Belarus)", "Chambre des représentants (Biélorussie)"),
          ("Macedoine", "Sobranie"): ("Assembly of North Macedonia", "Assemblée de la République de Macédoine du Nord"),
          ("Nouvelle-Caledonie", "Congrès"): ("Congress of New Caledonia", "Congrès de la Nouvelle-Calédonie"),
          ("Polynésie française", "Assemblée de la Polynésie française"): ("Assembly of French Polynesia", "Assemblée de la Polynésie française")}
pays = sorted({c["pays"] for c in chs if c["pays"] in iso})
articles = {}
for i in range(0, len(pays), 25):
    articles.update(U.articles_chambres([iso[p] for p in pays[i:i + 25]])); time.sleep(2)
st = {"exact": 0, "proche": 0, "en_seul": 0, "fr_seul": 0, "rien": 0}
for c in chs:
    arts = list(articles.get(iso.get(c["pays"], ""), []))
    if (c["pays"], c["chambre"]) in MANUEL: arts = [MANUEL[(c["pays"], c["chambre"])]]
    best = None
    for en, fr in arts:
        se = sf = None; info = ""
        try:
            if en:
                der, g, tib = CW.lire_infobox(en); se = U.sieges(g) if g else None; info += f" EN[{en}] {der} tot_ib={tib} {sorted(se or [], reverse=True)[:6]} Σ{sum(se or [])}"
            if fr:
                der2, g2 = CW.lire_infobox_fr(fr); sf = U.sieges(g2) if g2 else None; info += f" FR[{fr}] {der2} {sorted(sf or [], reverse=True)[:6]} Σ{sum(sf or [])}"
        except Exception as e: info += f" ERR {type(e).__name__}"
        ok_en = se and abs(sum(se) - c["total"]) <= 3
        ok_fr = sf and abs(sum(sf) - c["total"]) <= 3
        score = (2 if (ok_en and ok_fr and proche(se, sf)) else 0) + bool(ok_en) + bool(ok_fr)
        if not best or score > best[0]: best = (score, se, sf, ok_en, ok_fr, info)
        time.sleep(0.3)
    if not best: st["rien"] += 1; print(f"RIEN {c['pays']} / {c['chambre']} (total {c['total']}) : aucun article"); continue
    score, se, sf, ok_en, ok_fr, info = best
    if ok_en and ok_fr and se == sf: st["exact"] += 1; etat = "EXACT"
    elif ok_en and ok_fr and proche(se, sf): st["proche"] += 1; etat = "PROCHE"
    elif ok_en: st["en_seul"] += 1; etat = "EN_SEUL"
    elif ok_fr: st["fr_seul"] += 1; etat = "FR_SEUL"
    else: st["rien"] += 1; etat = "RIEN"
    print(f"{etat} {c['pays']} / {c['chambre']} (total {c['total']}) :{info}")
print("TOTAL", len(chs), json.dumps(st))
# Sources officielles
try:
    r = requests.get("https://www.abgeordnetenwatch.de/api/v2/parliament-periods", params={"parliament": 5, "type": "legislature", "range_end": 5, "sort_by": "id", "sort_direction": "desc"}, headers=UA, timeout=60).json()
    per = r["data"][0]; print("ABGW periode", per["id"], per["label"])
    m = requests.get("https://www.abgeordnetenwatch.de/api/v2/candidacies-mandates", params={"parliament_period": per["id"], "type": "mandate", "range_end": 1000}, headers=UA, timeout=120).json()
    cpt = {}
    for x in m["data"]:
        if x.get("end_date"): continue
        fm = [f for f in (x.get("fraction_membership") or []) if not f.get("valid_until")]
        lab = fm[0]["fraction"]["label"] if fm else "sans groupe"
        cpt[lab] = cpt.get(lab, 0) + 1
    print("ABGW", sum(cpt.values()), cpt)
except Exception as e: print("ABGW ERR", e)
try:
    z = requests.get("https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip", headers=UA, timeout=120)
    print("AN zip", z.status_code, len(z.content))
    zf = zipfile.ZipFile(io.BytesIO(z.content)); noms = zf.namelist(); print("AN fichiers", len(noms), noms[:3])
    organes = {}
    for n in noms:
        if "/organe/" in n:
            o = json.loads(zf.read(n))["organe"]
            if o.get("codeType") == "GP": organes[o["uid"]] = (o.get("libelleAbrev"), o.get("libelle"), o.get("couleurAssociee"))
    cpt = {}
    for n in noms:
        if "/acteur/" in n:
            a = json.loads(zf.read(n))["acteur"]; ms = a["mandats"]["mandat"]; ms = ms if isinstance(ms, list) else [ms]
            for mm in ms:
                if mm.get("typeOrgane") == "GP" and not mm.get("dateFin"):
                    ref = mm["organes"]["organeRef"]; cpt[ref] = cpt.get(ref, 0) + 1
    print("AN", sum(cpt.values()), {organes.get(k, (k,))[0]: v for k, v in cpt.items()}, list(organes.values())[:3])
except Exception as e: print("AN ERR", e)
