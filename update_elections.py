import requests
from supabase import create_client
from datetime import datetime, date, timedelta
import time
import os

# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════
# NORMALISATION DES NOMS DE PAYS
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
    "Macédoine du Nord":"Macedoine du Nord","Malaisie":"Malaisie",
    "Mauritanie":"Mauritanie","Mexique":"Mexique","Moldavie":"Moldavie",
    "Monténégro":"Montenegro","Mozambique":"Mozambique","Myanmar":"Myanmar",
    "Népal":"Nepal","Nicaragua":"Nicaragua","Nigéria":"Nigeria",
    "Norvège":"Norvege","Nouvelle-Zélande":"Nouvelle-Zelande",
    "Ouzbékistan":"Ouzbekistan","Papouasie-Nouvelle-Guinée":"Papouasie-NG",
    "Pérou":"Perou","République centrafricaine":"Centrafrique",
    "République de Corée":"Coree du Sud","République démocratique du Congo":"RD Congo",
    "République dominicaine":"Rep. dominicaine","République du Congo":"Rep. du Congo",
    "Roumanie":"Roumanie","Royaume-Uni":"Royaume-Uni",
    "São Tomé-et-Príncipe":"Sao Tome-et-Principe","Sénégal":"Senegal",
    "Slovaquie":"Slovaquie","Slovénie":"Slovenie","Somalie":"Somalie",
    "Soudan du Sud":"Soudan du Sud","Sri Lanka":"Sri Lanka",
    "Suède":"Suede","Syrie":"Syrie","Tadjikistan":"Tadjikistan",
    "Taïwan":"Taiwan","Tchad":"Tchad","Tchéquie":"Tchequie",
    "Thaïlande":"Thailande","Trinité-et-Tobago":"Trinidad & Tobago",
    "Tunisie":"Tunisie","Turkménistan":"Turkmenistan","Ukraine":"Ukraine",
    "Viêt Nam":"Vietnam","Vietnam":"Vietnam","Yémen":"Yemen",
    "États-Unis":"Etats-Unis","Émirats arabes unis":"Emirats arabes",
    "Liban":"Liban","Lettonie":"Lettonie","Lituanie":"Lituanie",
    "Pologne":"Pologne","Hongrie":"Hongrie","Bulgarie":"Bulgarie",
    "Albanie":"Albanie","Monténégro":"Montenegro","Serbie":"Serbie",
    "Croatie":"Croatie","Bosnie-Herzégovine":"Bosnie",
    "Jordanie":"Jordanie","Kazakhstan":"Kazakhstan","Kirghizstan":"Kirghizstan",
    "Ouganda":"Ouganda","Kenya":"Kenya","Ghana":"Ghana","Cameroun":"Cameroun",
    "Gabon":"Gabon","Togo":"Togo","Bénin":"Benin","Mali":"Mali",
    "Burkina Faso":"Burkina Faso","Niger":"Niger","Tchad":"Tchad",
    "Zambie":"Zambie","Zimbabwe":"Zimbabwe","Namibie":"Namibie",
    "Botswana":"Botswana","Lesotho":"Lesotho","Eswatini":"Eswatini",
    "Colombie":"Colombie","Chili":"Chili","Argentine":"Argentine",
    "Bolivie":"Bolivie","Paraguay":"Paraguay","Uruguay":"Uruguay",
    "Venezuela":"Venezuela","Suriname":"Suriname","Guyana":"Guyana",
    "Panama":"Panama","Guatemala":"Guatemala","Honduras":"Honduras",
    "El Salvador":"Salvador","Belize":"Belize","Cuba":"Cuba",
    "Jamaïque":"Jamaique","Haïti":"Haiti","Bahamas":"Bahamas",
    "Barbade":"Barbade","Trinité-et-Tobago":"Trinidad & Tobago",
}

def normaliser(pays):
    return NOMS_PAYS.get(pays, pays)

# ══════════════════════════════════════
# PAYS QID WIKIDATA
# ══════════════════════════════════════
PAYS_QID = {
    "Algerie":"Q262","Armenie":"Q399","Australie":"Q408",
    "Azerbaidjan":"Q227","Bangladesh":"Q902","Belarus":"Q184",
    "Belgique":"Q31","Benin":"Q962","Bolivie":"Q750",
    "Bosnie":"Q225","Bresil":"Q155","Bulgarie":"Q219",
    "Burkina Faso":"Q965","Burundi":"Q967","Cambodge":"Q424",
    "Cameroun":"Q1009","Canada":"Q16","Centrafrique":"Q929",
    "Chili":"Q298","Chine":"Q148","Chypre":"Q229",
    "Colombie":"Q739","Coree du Nord":"Q423","Coree du Sud":"Q884",
    "Costa Rica":"Q800","Cote d'Ivoire":"Q1020","Croatie":"Q224",
    "Cuba":"Q241","Danemark":"Q35","Djibouti":"Q977",
    "Egypte":"Q79","Equateur":"Q736","Erythree":"Q986",
    "Espagne":"Q29","Estonie":"Q191","Ethiopie":"Q115",
    "Fidji":"Q712","Finlande":"Q33","France":"Q142",
    "Gabon":"Q1000","Gambie":"Q1005","Georgie":"Q230",
    "Ghana":"Q117","Grece":"Q41","Guatemala":"Q774",
    "Guinee":"Q1006","Guinee-Bissau":"Q1007","Guyana":"Q734",
    "Haiti":"Q790","Honduras":"Q783","Hongrie":"Q28",
    "Inde":"Q668","Indonesie":"Q252","Irak":"Q796",
    "Iran":"Q794","Irlande":"Q27","Islande":"Q189",
    "Israel":"Q801","Italie":"Q38","Jamaique":"Q766",
    "Japon":"Q17","Jordanie":"Q810","Kazakhstan":"Q232",
    "Kenya":"Q114","Kirghizstan":"Q813","Kosovo":"Q1246",
    "Koweit":"Q817","Laos":"Q819","Liban":"Q822",
    "Lettonie":"Q211","Liberia":"Q1014","Libye":"Q1016",
    "Lituanie":"Q37","Luxembourg":"Q32","Macedoine du Nord":"Q221",
    "Madagascar":"Q1019","Malaisie":"Q833","Malawi":"Q1020b",
    "Mali":"Q912","Malte":"Q233","Maroc":"Q1028",
    "Mauritanie":"Q1025","Mexique":"Q96","Moldavie":"Q217",
    "Mongolie":"Q711","Montenegro":"Q236","Mozambique":"Q1029",
    "Myanmar":"Q836","Namibie":"Q1030","Nepal":"Q837",
    "Nicaragua":"Q811","Niger":"Q1032","Nigeria":"Q1033",
    "Norvege":"Q20","Nouvelle-Zelande":"Q664","Oman":"Q842",
    "Ouganda":"Q1036","Ouzbekistan":"Q265","Pakistan":"Q843",
    "Panama":"Q804","Papouasie-NG":"Q691","Paraguay":"Q733",
    "Pays-Bas":"Q55","Perou":"Q419","Philippines":"Q928",
    "Pologne":"Q36","Portugal":"Q45","Qatar":"Q846",
    "RD Congo":"Q974","Rep. du Congo":"Q971","Roumanie":"Q218",
    "Royaume-Uni":"Q145","Russie":"Q159","Rwanda":"Q1037",
    "Salvador":"Q792","Sao Tome-et-Principe":"Q1039",
    "Arabie Saoudite":"Q851","Senegal":"Q1041","Serbie":"Q403",
    "Sierra Leone":"Q1044","Singapour":"Q334","Slovaquie":"Q214",
    "Slovenie":"Q215","Somalie":"Q1045","Soudan":"Q1049",
    "Soudan du Sud":"Q958","Sri Lanka":"Q854","Suede":"Q34",
    "Suisse":"Q39","Syrie":"Q858","Tadjikistan":"Q863",
    "Taiwan":"Q865","Tanzanie":"Q924","Tchad":"Q657",
    "Tchequie":"Q213","Thailande":"Q869","Timor oriental":"Q574",
    "Togo":"Q945","Tonga":"Q678","Trinidad & Tobago":"Q754",
    "Tunisie":"Q948","Turquie":"Q43","Turkmenistan":"Q874",
    "Ukraine":"Q212","Uruguay":"Q77","Venezuela":"Q717",
    "Vietnam":"Q881","Yemen":"Q805","Zambie":"Q953",
    "Zimbabwe":"Q954","Etats-Unis":"Q30","Algerie":"Q262",
    "Armenie":"Q399","Montenegro":"Q236","Albanie":"Q222",
}

# ══════════════════════════════════════
# SOURCE 1 — WIKIDATA: DÉCOUVERTE
# ══════════════════════════════════════
QUERY_DECOUVERTE = """
SELECT DISTINCT ?paysLabel ?date ?typeLabel WHERE {
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

def decouvrir_elections():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Découverte Wikidata...")
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": QUERY_DECOUVERTE, "format": "json"},
            headers={"Accept":"application/json","User-Agent":"Geolandar/4.0"},
            timeout=45
        )
        r.raise_for_status()
        resultats = r.json()["results"]["bindings"]
        print(f"  {len(resultats)} élections trouvées")
        nouvelles = 0
        for row in resultats:
            pays_wd = row.get("paysLabel",{}).get("value","")
            pays = normaliser(pays_wd)
            date_el = row.get("date",{}).get("value","")[:10]
            if not pays or not date_el:
                continue
            try:
                res = supabase.table("elections").select("id")\
                    .eq("pays", pays).eq("date", date_el).execute()
                if not res.data:
                    supabase.table("elections").insert({
                        "pays": pays, "date": date_el,
                        "winner": "", "party": "",
                        "done": False,
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                    print(f"  + {pays} ({date_el})")
                    nouvelles += 1
            except:
                pass
        print(f"  {nouvelles} nouvelles élections ajoutées")
    except Exception as e:
        print(f"  Erreur découverte: {type(e).__name__}")

# ══════════════════════════════════════
# SOURCE 2 — WIKIDATA: RÉSULTATS
# ══════════════════════════════════════
def fetch_wikidata(pays, annee):
    qid = PAYS_QID.get(pays)
    if not qid:
        return None
    query = """
SELECT ?vainqueurLabel ?partiLabel ?date WHERE {
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 wd:""" + qid + """ .
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL { ?vainqueur wdt:P102 ?parti . }
  FILTER(YEAR(?date) = """ + str(annee) + """)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY DESC(?date)
LIMIT 1
"""
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept":"application/json","User-Agent":"Geolandar/4.0"},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        if data and data[0].get("vainqueurLabel",{}).get("value"):
            return {
                "winner": data[0]["vainqueurLabel"]["value"],
                "party":  data[0].get("partiLabel",{}).get("value",""),
                "date":   data[0].get("date",{}).get("value","")[:10],
                "source": "Wikidata"
            }
    except Exception as e:
        print(f"    Wikidata erreur: {type(e).__name__}")
    return None

# ══════════════════════════════════════
# SOURCE 3 — ACE ELECTORAL KNOWLEDGE
# ══════════════════════════════════════
def fetch_ace(pays, annee):
    """ACE Electoral Knowledge Network — ONU"""
    try:
        url = f"https://aceproject.org/epic-en/CDMap?question=ES005&view=country&Set=Yes"
        # ACE n'a pas d'API publique directe
        # On utilise leur endpoint de recherche
        r = requests.get(
            f"https://aceproject.org/ero-en/regions/countries/{pays[:3].upper()}",
            headers={"User-Agent":"Geolandar/4.0"},
            timeout=15
        )
        if r.status_code == 200 and str(annee) in r.text:
            return {"source": "ACE", "found": True}
    except:
        pass
    return None

# ══════════════════════════════════════
# SOURCE 4 — IPU PARLINE (Parlements)
# ══════════════════════════════════════
def fetch_ipu(pays, annee):
    """IPU Parline — Union Interparlementaire"""
    try:
        r = requests.get(
            f"https://data.ipu.org/api/election.json?lang=fr&chamber_id=all&year={annee}",
            headers={"User-Agent":"Geolandar/4.0"},
            timeout=20
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for item in data:
                    if pays.lower() in str(item.get("country_name","")).lower():
                        return {
                            "winner": item.get("winning_party",""),
                            "party":  item.get("winning_party",""),
                            "source": "IPU Parline"
                        }
    except:
        pass
    return None

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
    "Algerie":            ("FLN (Front de Libération Nationale)","FLN","2026-07-02"),
}

# ══════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════
def deja_enregistre(pays):
    try:
        res = supabase.table("elections").select("winner")\
            .eq("pays", pays).eq("done", True).execute()
        for row in res.data:
            w = row.get("winner","")
            if w and w not in ["","En cours de verification","undefined"]:
                return True
    except:
        pass
    return False

def save_supabase(pays, date_el, winner, party, source):
    try:
        supabase.table("elections").upsert({
            "pays": pays, "date": date_el,
            "winner": winner, "party": party,
            "done": True,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="pays,date").execute()
        print(f"  ✓ SUPABASE: {winner} ({source})")
        return True
    except Exception as e:
        print(f"  ✗ SUPABASE ERREUR: {e}")
        return False

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def est_passee(date_str):
    try:
        d = date_str.replace("-00","-15")
        return datetime.strptime(d[:10],"%Y-%m-%d").date() <= date.today()
    except:
        return False

def main():
    print("="*60)
    print("  GEOLANDAR — Mise à jour automatique v5.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)

    # ÉTAPE 1: Découvrir nouvelles élections
    print("\n[ÉTAPE 1] Découverte des élections...")
    decouvrir_elections()
    time.sleep(3)

    # ÉTAPE 2: Écrire résultats connus
    print("\n[ÉTAPE 2] Résultats vérifiés...")
    for pays, (winner, party, date_el) in RESULTATS_CONNUS.items():
        if not deja_enregistre(pays):
            save_supabase(pays, date_el, winner, party, "Manuel vérifié")
        else:
            print(f"  - {pays}: déjà enregistré")

    # ÉTAPE 3: Chercher résultats manquants
    print("\n[ÉTAPE 3] Recherche résultats manquants...")
    try:
        today = date.today().isoformat()
        res = supabase.table("elections").select("pays,date")\
            .eq("done", False).lte("date", today).execute()
        elections_sans = [r for r in res.data if r.get("pays")]
        print(f"  {len(elections_sans)} élections passées sans résultat")

        for row in elections_sans:
            pays = row["pays"]
            date_el = row.get("date","")
            if not date_el or not est_passee(date_el):
                continue
            annee = int(date_el[:4])
            print(f"\n  {pays} ({date_el})...")

            # Wikidata
            res_wd = fetch_wikidata(pays, annee)
            if res_wd and res_wd.get("winner"):
                save_supabase(pays, date_el, res_wd["winner"], res_wd["party"], "Wikidata")
                time.sleep(1)
                continue

            # IPU Parline
            res_ipu = fetch_ipu(pays, annee)
            if res_ipu and res_ipu.get("winner"):
                save_supabase(pays, date_el, res_ipu["winner"], res_ipu["party"], "IPU")
                time.sleep(1)
                continue

            print(f"  Aucune source n'a trouvé de résultat")
            time.sleep(1)

    except Exception as e:
        print(f"  Erreur étape 3: {e}")

    print(f"\n{'='*60}")
    print(f"  Terminé: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
