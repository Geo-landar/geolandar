import requests
from supabase import create_client
from datetime import datetime, date
import time
import os
import json
import re

# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════
# NORMALISATION NOMS DE PAYS
# ══════════════════════════════════════
NOMS_PAYS = {
    "Algérie":"Algerie","Arménie":"Armenie","Bélarus":"Belarus",
    "Bénin":"Benin","Brésil":"Bresil","Corée du Sud":"Coree du Sud",
    "Corée du Nord":"Coree du Nord","Côte d'Ivoire":"Cote d'Ivoire",
    "Érythrée":"Erythree","Éthiopie":"Ethiopie","Équateur":"Equateur",
    "Fédération de Russie":"Russie","Géorgie":"Georgie","Grèce":"Grece",
    "Guinée":"Guinee","Guinée-Bissau":"Guinee-Bissau",
    "Guinée équatoriale":"Guinee equatoriale","Haïti":"Haiti",
    "Îles Marshall":"Iles Marshall","Îles Salomon":"Iles Salomon",
    "Indonésie":"Indonesie","Israël":"Israel","Jamaïque":"Jamaique",
    "Macédoine du Nord":"Macedoine du Nord","Mauritanie":"Mauritanie",
    "Mexique":"Mexique","Moldavie":"Moldavie","Monténégro":"Montenegro",
    "Mozambique":"Mozambique","Myanmar":"Myanmar","Népal":"Nepal",
    "Nicaragua":"Nicaragua","Nigéria":"Nigeria","Norvège":"Norvege",
    "Nouvelle-Zélande":"Nouvelle-Zelande","Ouzbékistan":"Ouzbekistan",
    "Papouasie-Nouvelle-Guinée":"Papouasie-NG","Pérou":"Perou",
    "République centrafricaine":"Centrafrique",
    "République de Corée":"Coree du Sud",
    "République démocratique du Congo":"RD Congo",
    "République dominicaine":"Rep. dominicaine",
    "République du Congo":"Rep. du Congo",
    "Royaume-Uni":"Royaume-Uni",
    "São Tomé-et-Príncipe":"Sao Tome-et-Principe",
    "Sénégal":"Senegal","Slovénie":"Slovenie","Somalie":"Somalie",
    "Soudan du Sud":"Soudan du Sud","Sri Lanka":"Sri Lanka",
    "Suède":"Suede","Tadjikistan":"Tadjikistan","Taïwan":"Taiwan",
    "Tchéquie":"Tchequie","Thaïlande":"Thailande",
    "Trinité-et-Tobago":"Trinidad & Tobago","Tunisie":"Tunisie",
    "Turkménistan":"Turkmenistan","Ukraine":"Ukraine",
    "Viêt Nam":"Vietnam","Yémen":"Yemen","États-Unis":"Etats-Unis",
    "Émirats arabes unis":"Emirats arabes","Liban":"Liban",
    "Lettonie":"Lettonie","Lituanie":"Lituanie","Pologne":"Pologne",
    "Hongrie":"Hongrie","Bulgarie":"Bulgarie","Albanie":"Albanie",
    "Serbie":"Serbie","Croatie":"Croatie","Jordanie":"Jordanie",
    "Kazakhstan":"Kazakhstan","Kirghizstan":"Kirghizstan",
    "Ouganda":"Ouganda","Colombie":"Colombie","Chili":"Chili",
    "Argentine":"Argentine","Bolivie":"Bolivie","Venezuela":"Venezuela",
    "Suriname":"Suriname","Guyana":"Guyana","Panama":"Panama",
    "Guatemala":"Guatemala","Honduras":"Honduras",
    "El Salvador":"Salvador","Belize":"Belize","Cuba":"Cuba",
    "Barbade":"Barbade","Bosnie-Herzégovine":"Bosnie",
    "Monténégro":"Montenegro","Albanie":"Albanie",
}

def normaliser(pays):
    return NOMS_PAYS.get(pays, pays)

# ══════════════════════════════════════
# RÉSULTATS CONNUS ET VÉRIFIÉS
# ══════════════════════════════════════
RESULTATS_CONNUS = {
    "Colombie":           ("Abelardo de la Espriella","Defensores de la Patria","2026-06-21"),
    "Hongrie":            ("Péter Magyar","Tisza (conservateur pro-UE)","2026-04-12"),
    "Canada":             ("Mark Carney","Parti Libéral (centre)","2025-04-28"),
    "Coree du Sud":       ("Lee Jae-myung","Parti Démocrate (centre-gauche)","2025-06-03"),
    "Equateur":           ("Daniel Noboa","ADN (centre-droit)","2026-02-09"),
    "Albanie":            ("Edi Rama","PS (Parti Socialiste)","2026-05-11"),
    "Chypre":             ("DISY","DISY (centre-droit)","2026-05-24"),
    "Armenie":            ("Nikol Pachinian","Contrat civil (centre)","2026-06-07"),
    "Bahamas":            ("Philip Davis","PLP (centre-gauche)","2026-05-12"),
    "Costa Rica":         ("Laura Hernandez","PLN (centre-gauche)","2026-02-01"),
    "Barbade":            ("Mia Mottley","BLP (centre-gauche)","2026-02-11"),
    "Salvador":           ("Nayib Bukele","Nuevas Ideas (populiste)","2026-03-01"),
    "Antigua-et-Barbuda": ("Gaston Browne","ABLP (centre-gauche)","2026-04-30"),
    "Perou":              ("Keiko Fujimori","Fuerza Popular (droite)","2026-06-07"),
    "Japon":              ("Sanae Takaichi","PLD (conservateur)","2025-10-27"),
    "Algerie":            ("FLN","FLN (nationalisme autoritaire)","2026-07-02"),
    "Danemark":           ("Mette Frederiksen","Parti Social-Démocrate","2026-03-24"),
    "Bulgarie":           ("Rumen Radev","Bulgarie Progressiste","2026-04-19"),
    "Vietnam":            ("Parti Communiste du Vietnam","PCV","2026-03-15"),
    "Ouganda":            ("Yoweri Museveni","NRM","2026-01-15"),
    "Liban":              ("Nawaf Salam","Liste Ensemble pour le Changement","2026-05-10"),
    "Ethiopie":           ("Abiy Ahmed","Parti de la Prosperite (PP)","2026-06-01"),
    "Portugal":           ("Luis Montenegro","AD - Alliance Democratique","2025-03-16"),
    "Montenegro":         ("Milojko Spajic","Europe Maintenant","2026-03-15"),
    "Macedoine du Nord":  ("Hristijan Mickoski","VMRO-DPMNE","2026-04-01"),
    "Benin":              ("Patrice Talon","UP (Union Progressiste)","2026-04-12"),
}

# ══════════════════════════════════════
# SOURCE 1 — WIKIDATA GLOBAL (1 requête)
# ══════════════════════════════════════
QUERY_RESULTATS = """
SELECT ?paysLabel ?date ?vainqueurLabel ?partiLabel WHERE {
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(?date >= "2024-01-01"^^xsd:dateTime)
  FILTER(?date <= "2027-12-31"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY DESC(?date)
LIMIT 300
"""

# Découverte: inclut élections partielles (by-elections Q15284)
QUERY_DECOUVERTE = """
SELECT DISTINCT ?paysLabel ?date ?datePrecision ?typeLabel ?type WHERE {
  ?election wdt:P31 ?type .
  ?type wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election p:P585 ?dateStatement .
  ?dateStatement psv:P585 ?dateNode .
  ?dateNode wikibase:timeValue ?date .
  ?dateNode wikibase:timePrecision ?datePrecision .
  FILTER(?date >= "2025-01-01"^^xsd:dateTime)
  FILTER(?date <= "2029-12-31"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY ?date
LIMIT 400
"""

# QIDs des types d'élections partielles
TYPES_PARTIELLES = [
    "Q15284",   # by-election (élection partielle générique)
    "Q1198521", # élection partielle législative
    "Q82673",   # élection complémentaire
]

# Mots-clés (FR/EN) signalant une élection infranationale plutôt que nationale.
# Wikidata classe parfois des scrutins régionaux/locaux sous la même
# catégorie générique que les élections nationales (Q40231) — on les
# détecte donc via le libellé du type, faute de mieux.
MOTS_CLES_REGIONAL = [
    "regional","régional","state election","provincial","gubernatorial",
    "governor","land election","landtag","cantonal","municipal","local election",
    "municipale","cantonale","départementale","state legislature","assembly election (state)",
    "county","state senate","state house","by-election (state)","legislative assembly of",
]

# ══════════════════════════════════════
# SOURCE COMPLÉMENTAIRE — WIKIDATA PAR VOTES
# P991 (vainqueur direct) n'existe que sur ~23% des élections référencées.
# Cette requête déduit le vainqueur via P726 (candidat) + P1111 (votes reçus),
# en prenant le candidat avec le plus de voix — couvre bien plus de pays.
# ══════════════════════════════════════
QUERY_RESULTATS_VOTES = """
SELECT ?paysLabel ?date ?candLabel ?votes ?partiLabel WHERE {
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election wdt:P585 ?date .
  ?election p:P726 ?candStatement .
  ?candStatement ps:P726 ?cand .
  ?candStatement pq:P1111 ?votes .
  OPTIONAL { ?cand wdt:P102 ?parti . }
  FILTER(?date >= "2024-01-01"^^xsd:dateTime)
  FILTER(?date <= "2027-12-31"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY DESC(?date)
LIMIT 600
"""

def wikidata_query(query, label=""):
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept":"application/json","User-Agent":"Geolandar/5.2"},
            timeout=60
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        print(f"  Wikidata {label}: {len(data)} résultats")
        return data
    except Exception as e:
        print(f"  Wikidata erreur {label}: {type(e).__name__}")
        return []

def fetch_wikidata_resultats():
    data = wikidata_query(QUERY_RESULTATS, "résultats")
    par_pays = {}
    today = date.today().isoformat()
    for row in data:
        pays = normaliser(row.get("paysLabel",{}).get("value",""))
        winner = row.get("vainqueurLabel",{}).get("value","")
        party = row.get("partiLabel",{}).get("value","")
        date_el = row.get("date",{}).get("value","")[:10]
        if not pays or not winner or winner=="undefined": continue
        if date_el > today: continue
        if pays not in par_pays:
            par_pays[pays] = {"winner":winner,"party":party,"date":date_el}
    return par_pays

def fetch_wikidata_resultats_votes():
    """Source complémentaire : déduit le vainqueur par le nombre de voix le plus élevé
    (candidat + votes reçus). Utile pour les élections où P991 (vainqueur direct)
    n'est pas renseigné sur Wikidata."""
    data = wikidata_query(QUERY_RESULTATS_VOTES, "résultats (par votes)")
    par_election = {}
    today = date.today().isoformat()
    for row in data:
        pays = normaliser(row.get("paysLabel",{}).get("value",""))
        date_el = row.get("date",{}).get("value","")[:10]
        cand = row.get("candLabel",{}).get("value","")
        parti = row.get("partiLabel",{}).get("value","")
        votes_raw = row.get("votes",{}).get("value","")
        if not pays or not cand or not date_el or date_el > today: continue
        try:
            votes = float(votes_raw)
        except (ValueError, TypeError):
            continue
        key = (pays, date_el)
        if key not in par_election or votes > par_election[key]["votes"]:
            par_election[key] = {"winner":cand,"party":parti,"votes":votes,"date":date_el}
    # Garder l'élection la plus récente par pays
    par_pays = {}
    for (pays, date_el), info in par_election.items():
        if pays not in par_pays or date_el > par_pays[pays]["date"]:
            par_pays[pays] = info
    return par_pays

def decouvrir_elections():
    data = wikidata_query(QUERY_DECOUVERTE, "découverte")
    nouvelles = 0
    ignorees = 0
    for row in data:
        pays = normaliser(row.get("paysLabel",{}).get("value",""))
        date_brute = row.get("date",{}).get("value","")[:10]
        type_qid = row.get("type",{}).get("value","").split("/")[-1]
        type_label = row.get("typeLabel",{}).get("value","")
        try:
            precision = int(row.get("datePrecision",{}).get("value","0"))
        except (ValueError, TypeError):
            precision = 0

        # GARDE-FOU 1 : sans pays, sans date, ou sans type identifié, on
        # n'insère rien plutôt que de créer une ligne incomplète trompeuse
        if not pays or not date_brute or not type_label:
            ignorees += 1
            continue

        # GARDE-FOU 2 : reconstruire la date selon la précision RÉELLE connue
        # par Wikidata, au lieu de faire confiance à la valeur brute qui
        # retombe souvent sur le 1er janvier quand seule l'année est connue.
        # Précisions Wikidata : 11 = jour, 10 = mois, 9 = année, <9 = trop vague
        annee, mois, jour = date_brute[:4], date_brute[5:7], date_brute[8:10]
        if precision >= 11:
            date_el = f"{annee}-{mois}-{jour}"
            cert = 1
        elif precision == 10:
            date_el = f"{annee}-{mois}-00"
            cert = 2
        elif precision == 9:
            date_el = f"{annee}-00-00"
            cert = 3
        else:
            # Précision inconnue ou trop vague (< année) : on ignore plutôt
            # que d'inventer une date
            ignorees += 1
            continue

        is_partial = type_qid in TYPES_PARTIELLES or any(
            k in type_label.lower() for k in ["partielle","by-election","partiel","complementaire"]
        )
        niveau = "regionale" if any(k in type_label.lower() for k in MOTS_CLES_REGIONAL) else "national"
        try:
            res = supabase.table("elections").select("id")\
                .eq("pays",pays).eq("date",date_el).execute()
            if not res.data:
                supabase.table("elections").insert({
                    "pays":pays,"date":date_el,
                    "winner":"","party":"","done":False,
                    "partial": is_partial,
                    "type": type_label,
                    "cert": cert,
                    "niveau": niveau,
                    "updated_at":datetime.now().isoformat()
                }).execute()
                marker = " [PARTIELLE]" if is_partial else ""
                marker += " [RÉGIONALE]" if niveau=="regionale" else ""
                precis = {1:"jour exact",2:"mois connu",3:"année seule"}[cert]
                print(f"  + {pays} ({date_el}, {precis}){marker}")
                nouvelles += 1
        except: pass
    print(f"  {nouvelles} nouvelles élections ajoutées, {ignorees} ignorées (données insuffisantes)")

# ══════════════════════════════════════
# SOURCE 2 — WIKIPEDIA (résultats manquants)
# ══════════════════════════════════════
def fetch_wikipedia(pays, annee, lang="fr"):
    """Cherche le résultat d'une élection sur Wikipedia (FR par défaut, EN en repli)"""
    site = "fr.wikipedia.org" if lang == "fr" else "en.wikipedia.org"
    query = (f"élection {pays} {annee} résultat vainqueur" if lang == "fr"
             else f"{pays} election {annee} result winner")
    headers = {"User-Agent":"Geolandar/5.2 (geo-landar.github.io)"}

    try:
        r = requests.get(
            f"https://{site}/w/api.php",
            params={
                "action":"query","list":"search",
                "srsearch":query,
                "format":"json","srlimit":5,
                "srprop":"snippet|titlesnippet"
            },
            headers=headers, timeout=15
        )
        if r.status_code == 200:
            results = r.json().get("query",{}).get("search",[])
            for res in results:
                titre = res["title"]
                if str(annee) in titre and pays[:4].lower() in titre.lower():
                    r2 = requests.get(
                        f"https://{site}/api/rest_v1/page/summary/{titre.replace(' ','_')}",
                        headers=headers, timeout=15
                    )
                    if r2.status_code == 200:
                        data = r2.json()
                        extract = data.get("extract","")
                        winner = extraire_vainqueur(extract, lang)
                        if winner:
                            return {"winner":winner,"party":"","source":f"Wikipedia-{lang.upper()}"}
    except Exception as e:
        print(f"    Wikipedia({lang}) erreur: {type(e).__name__}")
    return None

def extraire_vainqueur(texte, lang="fr"):
    """Extrait le nom du vainqueur depuis un texte Wikipedia (FR ou EN)"""
    if lang == "fr":
        patterns = [
            r"(?:remporte|élu|élu président|vainqueur|gagne)[^\n\.]*?([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})",
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})\s+(?:remporte|est élu|gagne|l'emporte)",
            r"élu avec\s+\d+[^\n]*?([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})",
        ]
        mots_exclus = ["Le","La","Les","Un","Une","Dans","Pour","Sur","Avec","Cette"]
    else:
        patterns = [
            r"(?:won by|elected|winner|defeated|re-?elected)[^\n\.]*?([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})",
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\s+(?:won|was elected|defeated|secured)",
        ]
        mots_exclus = ["The","This","That","With","From","After","Following"]
    for pattern in patterns:
        m = re.search(pattern, texte)
        if m:
            nom = m.group(1).strip()
            # Filtrer les faux positifs
            if nom.split()[0] not in mots_exclus and len(nom) > 4:
                return nom
    return None

# ══════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════
def deja_enregistre(pays):
    try:
        res = supabase.table("elections").select("winner")\
            .eq("pays",pays).eq("done",True).execute()
        for row in res.data:
            w = row.get("winner","")
            if w and w not in ["","undefined","En cours de verification"]:
                return True
    except: pass
    return False

def save(pays, date_el, winner, party, source=""):
    try:
        supabase.table("elections").upsert({
            "pays":pays,"date":date_el,
            "winner":winner,"party":party,"done":True,
            "updated_at":datetime.now().isoformat()
        }, on_conflict="pays,date").execute()
        print(f"  ✓ {pays}: {winner} ({source})")
        return True
    except Exception as e:
        print(f"  ✗ {pays}: {e}")
        return False

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def main():
    print("="*55)
    print("  GEOLANDAR — Mise à jour automatique v5.3")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*55)
    today = date.today().isoformat()
    total = 0

    # ÉTAPE 1: Découvrir nouvelles élections + partielles
    print("\n[1] Découverte élections (nationales + partielles)...")
    decouvrir_elections()
    time.sleep(3)

    # ÉTAPE 2: Résultats vérifiés manuellement
    print("\n[2] Résultats vérifiés...")
    for pays,(winner,party,date_el) in RESULTATS_CONNUS.items():
        if not deja_enregistre(pays):
            if save(pays,date_el,winner,party,"Manuel"):
                total += 1
        else:
            print(f"  - {pays}: déjà OK")

    # ÉTAPE 3: Wikidata (1 requête globale)
    print("\n[3] Wikidata — résultats globaux (vainqueur direct)...")
    time.sleep(2)
    resultats_wd = fetch_wikidata_resultats()
    for pays, res in resultats_wd.items():
        if deja_enregistre(pays): continue
        if res["date"] > today: continue
        if save(pays,res["date"],res["winner"],res["party"],"Wikidata"):
            total += 1

    # ÉTAPE 3bis: Wikidata — source complémentaire par votes (couvre plus de pays)
    print("\n[3bis] Wikidata — résultats déduits par votes (complémentaire)...")
    time.sleep(2)
    resultats_wd_votes = fetch_wikidata_resultats_votes()
    for pays, res in resultats_wd_votes.items():
        if deja_enregistre(pays): continue
        if res["date"] > today: continue
        if save(pays,res["date"],res["winner"],res["party"],"Wikidata-votes"):
            total += 1

    # ÉTAPE 4: Wikipedia — résultats manquants (FR puis EN en repli)
    print("\n[4] Wikipedia — résultats manquants (FR puis EN)...")
    try:
        res = supabase.table("elections").select("pays,date")\
            .eq("done",False).lte("date",today).execute()
        sans_resultat = [r for r in res.data if r.get("pays")]
        print(f"  {len(sans_resultat)} élections sans résultat")
        for row in sans_resultat[:40]:  # Augmenté de 20 à 40 pays traités par exécution
            pays = row["pays"]
            date_el = row.get("date","")
            if not date_el: continue
            annee = int(date_el[:4])
            print(f"  Wikipedia: {pays} ({annee})...")
            res_wp = fetch_wikipedia(pays, annee, "fr")
            if not res_wp:
                res_wp = fetch_wikipedia(pays, annee, "en")
            if res_wp and res_wp.get("winner"):
                if save(pays,date_el,res_wp["winner"],res_wp["party"],res_wp.get("source","Wikipedia")):
                    total += 1
            time.sleep(0.5)
    except Exception as e:
        print(f"  Erreur étape 4: {e}")

    print(f"\n{'='*55}")
    print(f"  TOTAL: {total} mises à jour")
    print(f"  Terminé: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
