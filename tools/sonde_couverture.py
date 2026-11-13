# Diagnostic temporaire : couverture des sources pour les 180 chambres (aucune écriture)
import json, os, sys, time
sys.path.insert(0, ".")
os.environ["SUPABASE_KEY"] = ""
import update_regions as U, chambres_wiki as CW
d = json.load(open("data/regions_chambres.json"))
iso = U.iso_des_pays()
chs = d["chambres"]
pays = sorted({c["pays"] for c in chs if c["pays"] in iso})
articles = {}
for i in range(0, len(pays), 25):
    articles.update(U.articles_chambres([iso[p] for p in pays[i:i + 25]])); time.sleep(2)
stats = {"en": 0, "fr": 0, "accord": 0, "aucun_article": 0}
lignes = []
for c in chs:
    arts = articles.get(iso.get(c["pays"], ""), [])
    if not arts: stats["aucun_article"] += 1; lignes.append(f"{c['pays']} / {c['chambre']} : aucun article"); continue
    best = ("", "", None, None)
    for en, fr in arts:
        se = sf = None
        try:
            if en:
                _, g, tib = CW.lire_infobox(en); s = sum(x["s"] for x in g)
                if g and (s == c["total"] or (tib and s == tib) or abs(s - c["total"]) <= 3): se = U.sieges(g)
            if fr:
                _, g2 = CW.lire_infobox_fr(fr); s2 = sum(x["s"] for x in g2)
                if g2 and abs(s2 - c["total"]) <= 3: sf = U.sieges(g2)
        except Exception: pass
        if se or sf:
            if (se and sf) or not best[2]: best = (en, fr, se, sf)
        time.sleep(0.3)
    en, fr, se, sf = best
    stats["en"] += bool(se); stats["fr"] += bool(sf); stats["accord"] += bool(se and sf and se == sf)
    lignes.append(f"{c['pays']} / {c['chambre']} : en={'oui' if se else 'non'} fr={'oui' if sf else 'non'} accord={'oui' if (se and sf and se == sf) else 'non'}")
print("TOTAL", len(chs), json.dumps(stats))
print("\n".join(lignes))
