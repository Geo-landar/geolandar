import requests
from supabase import create_client
from datetime import datetime, date, timedelta
import time
import os


# ══════════════════════════════════════
# NORMALISATION DES NOMS DE PAYS
# Wikidata -> nom dans le fichier HTML
# ══════════════════════════════════════
NOMS_PAYS = {
    # Accents
    "Algérie": "Algerie",
    "Arménie": "Armenie",
    "Bélarus": "Belarus",
    "Bénin": "Benin",
    "Brésil": "Bresil",
    "Chypre": "Chypre",
    "Corée du Sud": "Coree du Sud",
    "Corée du Nord": "Coree du Nord",
    "Côte d'Ivoire": "Cote d'Ivoire",
    "Érythrée": "Erythree",
    "Éthiopie": "Ethiopie",
    "Équateur": "Equateur",
    "Fédération de Russie": "Russie",
    "Géorgie": "Georgie",
    "Grèce": "Grece",
    "Guinée": "Guinee",
    "Guinée-Bissau": "Guinee-Bissau",
    "Guinée équatoriale": "Guinee equatoriale",
    "Haïti": "Haiti",
    "Hongrie": "Hongrie",
    "Îles Marshall": "Iles Marshall",
    "Îles Salomon": "Iles Salomon",
    "Indonésie": "Indonesie",
    "Irak": "Irak",
    "Islande": "Islande",
    "Israël": "Israel",
    "Italie": "Italie",
    "Jamaïque": "Jamaique",
    "Jordanie": "Jordanie",
    "Liban": "Liban",
    "Lettonie": "Lettonie",
    "Lituanie": "Lituanie",
    "Macédoine du Nord": "Macedoine du Nord",
    "Malaisie": "Malaisie",
    "Mali": "Mali",
    "Mauritanie": "Mauritanie",
    "Mexique": "Mexique",
    "Moldavie": "Moldavie",
    "Mongolie": "Mongolie",
    "Monténégro": "Montenegro",
    "Mozambique": "Mozambique",
    "Myanmar": "Myanmar",
    "Népal": "Nepal",
    "Nicaragua": "Nicaragua",
    "Nigéria": "Nigeria",
    "Norvège": "Norvege",
    "Nouvelle-Zélande": "Nouvelle-Zelande",
    "Ouzbékistan": "Ouzbekistan",
    "Ouganda": "Ouganda",
    "Pakistan": "Pakistan",
    "Papouasie-Nouvelle-Guinée": "Papouasie-NG",
    "Pérou": "Perou",
    "Philippines": "Philippines",
    "Pologne": "Pologne",
    "Portugal": "Portugal",
    "République centrafricaine": "Centrafrique",
    "République de Corée": "Coree du Sud",
    "République démocratique du Congo": "RD Congo",
    "République dominicaine": "Rep. dominicaine",
    "République du Congo": "Rep. du Congo",
    "Roumanie": "Roumanie",
    "Royaume-Uni": "Royaume-Uni",
    "Russie": "Russie",
    "São Tomé-et-Príncipe": "Sao Tome-et-Principe",
    "Sénégal": "Senegal",
    "Serbie": "Serbie",
    "Sierra Leone": "Sierra Leone",
    "Slovaquie": "Slovaquie",
    "Slovénie": "Slovenie",
    "Somalie": "Somalie",
    "Soudan": "Soudan",
    "Soudan du Sud": "Soudan du Sud",
    "Sri Lanka": "Sri Lanka",
    "Suède": "Suede",
    "Suisse": "Suisse",
    "Syrie": "Syrie",
    "Tadjikistan": "Tadjikistan",
    "Taïwan": "Taiwan",
    "Tanzanie": "Tanzanie",
    "Tchad": "Tchad",
    "Tchéquie": "Tchequie",
    "Thaïlande": "Thailande",
    "Timor oriental": "Timor oriental",
    "Togo": "Togo",
    "Trinité-et-Tobago": "Trinidad & Tobago",
    "Tunisie": "Tunisie",
    "Turkménistan": "Turkmenistan",
    "Turquie": "Turquie",
    "Ukraine": "Ukraine",
    "Uruguay": "Uruguay",
    "Venezuela": "Venezuela",
    "Viêt Nam": "Vietnam",
    "Vietnam": "Vietnam",
    "Yémen": "Yemen",
    "Zambie": "Zambie",
    "Zimbabwe": "Zimbabwe",
    "États-Unis": "Etats-Unis",
    "Émirats arabes unis": "Emirats arabes",
}

def normaliser_pays(pays_wikidata):
    """Convertit un nom de pays Wikidata vers le nom du fichier HTML"""
    return NOMS_PAYS.get(pays_wikidata, pays_wikidata)


# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════
# PARTIE 1 — DÉCOUVERTE AUTOMATIQUE
# Interroge Wikidata pour trouver toutes
# les élections dans les 3 prochaines années
# ══════════════════════════════════════

QUERY_DECOUVERTE = """
SELECT DISTINCT ?election ?electionLabel ?paysLabel ?date ?type ?typeLabel WHERE {
  ?election wdt:P31 ?type .
  ?type wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  ?election wdt:P585 ?date .
  FILTER(?date >= "2025-01-01"^^xsd:dateTime)
  FILTER(?date <= "2028-12-31"^^xsd:dateTime)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY ?date
LIMIT 200
"""

def decouvrir_elections():
    """Interroge Wikidata pour trouver toutes les élections à venir"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Découverte des élections sur Wikidata...")
    headers = {
        "Accept": "application/json",
        "User-Agent": "Geolandar/3.0 (github.com/Geo-landar)"
    }
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": QUERY_DECOUVERTE, "format": "json"},
            headers=headers,
            timeout=45
        )
        r.raise_for_status()
        resultats = r.json()["results"]["bindings"]
        print(f"  {len(resultats)} élections trouvées sur Wikidata")

        nouvelles = 0
        for row in resultats:
            pays = row.get("paysLabel", {}).get("value", "")
            date_el = row.get("date", {}).get("value", "")[:10]
            type_el = row.get("typeLabel", {}).get("value", "")

            if not pays or not date_el:
                continue

            # Vérifier si cette élection existe déjà dans Supabase
            try:
                pays_normalise = normaliser_pays(pays)
                res = supabase.table("elections") \
                    .select("id") \
                    .eq("pays", pays_normalise) \
                    .eq("date", date_el) \
                    .execute()

                if not res.data:
                    # Nouvelle élection — l'ajouter dans Supabase
                    pays_normalise = normaliser_pays(pays)
                    supabase.table("elections").insert({
                        "pays":       pays_normalise,
                        "date":       date_el,
                        "winner":     "",
                        "party":      "",
                        "done":       False,
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                    print(f"  + Nouvelle élection: {pays} ({date_el}) — {type_el}")
                    nouvelles += 1
            except:
                pass

        print(f"  {nouvelles} nouvelles élections ajoutées dans Supabase")
        return True

    except Exception as e:
        print(f"  Erreur découverte: {type(e).__name__} — {e}")
        return False

# ══════════════════════════════════════
# PARTIE 2 — MISE À JOUR DES RÉSULTATS
# Pour chaque élection passée sans résultat,
# cherche le vainqueur sur Wikidata
# ══════════════════════════════════════

# Résultats connus et vérifiés — écrits directement sans passer par Wikidata
RESULTATS_CONNUS = {
    "Colombie":           ("Abelardo de la Espriella", "Defensores de la Patria (extrême droite)", "2026-06-21"),
    "Hongrie":            ("Péter Magyar",             "Tisza (conservateur pro-UE)",              "2026-04-12"),
    "Canada":             ("Mark Carney",              "Parti Libéral (centre)",                   "2025-04-28"),
    "Coree du Sud":       ("Lee Jae-myung",            "Parti Démocrate (centre-gauche)",          "2025-06-03"),
    "Equateur":           ("Daniel Noboa",             "ADN (centre-droit)",                       "2026-02-09"),
    "Albanie":            ("Edi Rama",                 "PS (Parti Socialiste)",                    "2026-05-11"),
    "Chypre":             ("DISY",                     "DISY (centre-droit)",                      "2026-05-24"),
    "Armenie":            ("Nikol Pachinian",          "Contrat civil (centre)",                   "2026-06-07"),
    "Bahamas":            ("Philip Davis",             "PLP (centre-gauche)",                      "2026-05-12"),
    "Costa Rica":         ("Laura Hernandez",          "PLN (centre-gauche)",                      "2026-02-01"),
    "Barbade":            ("Mia Mottley",              "BLP (centre-gauche)",                      "2026-02-11"),
    "Salvador":           ("Nayib Bukele",             "Nuevas Ideas (populiste)",                 "2026-03-01"),
    "Antigua-et-Barbuda": ("Gaston Browne",            "ABLP (centre-gauche)",                     "2026-04-30"),
}

PAYS_QID = {
    "Ouganda":"Q1036","Danemark":"Q35","Bulgarie":"Q219",
    "Vietnam":"Q881","Montenegro":"Q236","Macedoine du Nord":"Q221",
    "Benin":"Q962","Liban":"Q822","Perou":"Q419","Zambie":"Q953",
    "Israel":"Q801","Bresil":"Q155","Suede":"Q34",
    "Nouvelle-Zelande":"Q664","Gambie":"Q1005","Algerie":"Q262",
    "Ouganda":"Q1036","Japon":"Q17","Turquie":"Q43","Pologne":"Q36",
    "Nigeria":"Q1033","Italie":"Q38","Argentine":"Q414",
    "Maroc":"Q1028","Pakistan":"Q843","Royaume-Uni":"Q145",
}

def fetch_wikidata_resultat(pays, annee):
    """Cherche le vainqueur d'une élection sur Wikidata"""
    qid = PAYS_QID.get(pays)
    if not qid:
        return None

    query = """
SELECT ?vainqueurLabel ?partiLabel WHERE {
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 wd:""" + qid + """ .
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(YEAR(?date) = """ + str(annee) + """)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
LIMIT 1
"""
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept":"application/json","User-Agent":"Geolandar/3.0"},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        if data and data[0].get("vainqueurLabel", {}).get("value"):
            return {
                "winner": data[0]["vainqueurLabel"]["value"],
                "party":  data[0].get("partiLabel", {}).get("value", ""),
                "date":   data[0].get("date", {}).get("value", "")[:10] if data[0].get("date") else "",
            }
    except:
        pass
    return None

def maj_resultats():
    """Met à jour les résultats des élections passées"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Mise à jour des résultats...")

    # 1. Écrire les résultats connus
    print(f"  Résultats connus: {len(RESULTATS_CONNUS)}")
    for pays, (winner, party, date_el) in RESULTATS_CONNUS.items():
        try:
            # Vérifier si déjà enregistré avec ce vainqueur
            res = supabase.table("elections") \
                .select("winner") \
                .eq("pays", pays) \
                .eq("done", True) \
                .execute()
            deja = any(r.get("winner") == winner for r in res.data)
            if deja:
                continue

            supabase.table("elections").upsert({
                "pays": pays, "date": date_el,
                "winner": winner, "party": party,
                "done": True,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="pays,date").execute()
            print(f"  OK: {pays} → {winner}")
        except Exception as e:
            print(f"  Erreur {pays}: {e}")

    # 2. Chercher les résultats manquants sur Wikidata
    print(f"\n  Recherche résultats manquants sur Wikidata...")
    try:
        today = date.today().isoformat()
        res = supabase.table("elections") \
            .select("pays,date,winner") \
            .eq("done", False) \
            .lte("date", today) \
            .execute()

        elections_sans_resultat = [
            r for r in res.data
            if not r.get("winner")
        ]
        print(f"  {len(elections_sans_resultat)} élections sans résultat")

        for row in elections_sans_resultat:
            pays = normaliser_pays(row["pays"])
            date_el = row["date"]
            annee = int(date_el[:4]) if date_el else 2026

            print(f"  Wikidata: {pays} ({date_el})...")
            resultat = fetch_wikidata_resultat(pays, annee)
            if resultat and resultat["winner"]:
                try:
                    # Pour les élections à 2 tours: utiliser la date du résultat
                    # pas forcément la date du 1er tour
                    date_resultat = resultat.get("date", date_el) or date_el
                    supabase.table("elections").upsert({
                        "pays": pays, "date": date_resultat,
                        "winner": resultat["winner"],
                        "party": resultat["party"],
                        "done": True,
                        "updated_at": datetime.now().isoformat()
                    }, on_conflict="pays,date").execute()
                    print(f"  OK: {pays} -> {resultat['winner']} ({date_resultat})")
                except Exception as e:
                    print(f"  Erreur Supabase: {e}")
            else:
                print(f"  Pas encore de resultat")
            time.sleep(1)

    except Exception as e:
        print(f"  Erreur lecture Supabase: {e}")

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def main():
    print("=" * 60)
    print("  GEOLANDAR - Mise à jour automatique v4.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    # Étape 1: Découvrir les nouvelles élections
    decouvrir_elections()
    time.sleep(2)

    # Étape 2: Mettre à jour les résultats
    maj_resultats()

    print(f"\n{'=' * 60}")
    print(f"  Terminé: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
