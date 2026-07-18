import requests
from supabase import create_client
from datetime import datetime, date
import time
import os

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
    "République du Congo":"Rep. du Congo","Roumanie":"Roumanie",
    "Royaume-Uni":"Royaume-Uni","São Tomé-et-Príncipe":"Sao Tome-et-Principe",
    "Sénégal":"Senegal","Slovaquie":"Slovaquie","Slovénie":"Slovenie",
    "Somalie":"Somalie","Soudan du Sud":"Soudan du Sud",
    "Sri Lanka":"Sri Lanka","Suède":"Suede","Syrie":"Syrie",
    "Tadjikistan":"Tadjikistan","Taïwan":"Taiwan","Tchad":"Tchad",
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
    "Guatemala":"Guatemala","Honduras":"Honduras","El Salvador":"Salvador",
    "Belize":"Belize","Cuba":"Cuba","Barbade":"Barbade",
    "Bosnie-Herzégovine":"Bosnie","Bosnie":"Bosnie",
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
}

# ══════════════════════════════════════
# SOURCE 1 — WIKIDATA (UNE SEULE REQUÊTE GLOBALE)
# ══════════════════════════════════════
QUERY_GLOBAL = """
SELECT ?paysLabel ?date ?vainqueurLabel ?partiLabel WHERE {
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(?date >= "2025-01-01"^^xsd:dateTime)
  FILTER(?date <= "2027-12-31"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY DESC(?date)
LIMIT 200
"""

QUERY_DECOUVERTE = """
SELECT DISTINCT ?paysLabel ?date WHERE {
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election wdt:P585 ?date .
  FILTER(?date >= "2025-01-01"^^xsd:dateTime)
  FILTER(?date <= "2029-12-31"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY ?date
LIMIT 300
"""

def fetch_wikidata_global():
    """Une seule requête pour tous les résultats — beaucoup plus rapide"""
    print(f"  Requête Wikidata globale...")
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": QUERY_GLOBAL, "format": "json"},
            headers={"Accept":"application/json","User-Agent":"Geolandar/5.0"},
            timeout=60
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        print(f"  {len(data)} résultats trouvés")
        # Grouper par pays — garder le plus récent
        par_pays = {}
        for row in data:
            pays_wd = row.get("paysLabel",{}).get("value","")
            pays = normaliser(pays_wd)
            winner = row.get("vainqueurLabel",{}).get("value","")
            party = row.get("partiLabel",{}).get("value","")
            date_el = row.get("date",{}).get("value","")[:10]
            if not pays or not winner or winner == "undefined":
                continue
            if pays not in par_pays:
                par_pays[pays] = {"winner":winner,"party":party,"date":date_el}
        return par_pays
    except Exception as e:
        print(f"  Erreur Wikidata: {type(e).__name__}")
        return {}

def decouvrir_wikidata():
    """Découvrir nouvelles élections en une seule requête"""
    print(f"  Découverte Wikidata...")
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": QUERY_DECOUVERTE, "format": "json"},
            headers={"Accept":"application/json","User-Agent":"Geolandar/5.0"},
            timeout=60
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        print(f"  {len(data)} élections trouvées sur Wikidata")
        today = date.today().isoformat()
        nouvelles = 0
        for row in data:
            pays_wd = row.get("paysLabel",{}).get("value","")
            pays = normaliser(pays_wd)
            date_el = row.get("date",{}).get("value","")[:10]
            if not pays or not date_el:
                continue
            try:
                res = supabase.table("elections").select("id")\
                    .eq("pays",pays).eq("date",date_el).execute()
                if not res.data:
                    supabase.table("elections").insert({
                        "pays":pays,"date":date_el,
                        "winner":"","party":"","done":False,
                        "updated_at":datetime.now().isoformat()
                    }).execute()
                    nouvelles += 1
            except:
                pass
        print(f"  {nouvelles} nouvelles élections ajoutées")
    except Exception as e:
        print(f"  Erreur découverte: {type(e).__name__}")

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
    except:
        pass
    return False

def save(pays, date_el, winner, party, source):
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
    print("  GEOLANDAR — Mise à jour v5.1 (optimisée)")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*55)
    today = date.today().isoformat()
    total = 0

    # ÉTAPE 1: Découvrir nouvelles élections (1 requête)
    print("\n[1] Découverte des élections...")
    decouvrir_wikidata()
    time.sleep(2)

    # ÉTAPE 2: Résultats connus — écriture directe
    print("\n[2] Résultats vérifiés...")
    for pays,(winner,party,date_el) in RESULTATS_CONNUS.items():
        if not deja_enregistre(pays):
            if save(pays,date_el,winner,party,"Manuel"):
                total += 1
        else:
            print(f"  - {pays}: déjà OK")

    # ÉTAPE 3: Wikidata global (1 seule requête pour tout)
    print("\n[3] Résultats Wikidata (requête globale)...")
    time.sleep(2)
    resultats_wd = fetch_wikidata_global()
    for pays, res in resultats_wd.items():
        if deja_enregistre(pays):
            continue
        if res["date"] > today:
            continue  # Ne pas écrire de résultat futur
        if save(pays, res["date"], res["winner"], res["party"], "Wikidata"):
            total += 1

    print(f"\n{'='*55}")
    print(f"  TOTAL: {total} mises à jour")
    print(f"  Terminé: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
