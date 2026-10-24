import requests
from supabase import create_client
from datetime import datetime, date, timedelta
import time
import os
import re

# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Mise à jour automatique des élections — v6.0 (24/10/2026)
#  Corrections par rapport à la v5.3 :
#   1. DÉCOUVERTE : la requête triait par date croissante avec une limite de
#      400 lignes à partir du 01/01/2025 — elle ne renvoyait donc QUE de
#      vieilles élections 2025 et n'atteignait jamais celles à venir
#      (Espagne, Brésil…). Fenêtre désormais : 90 jours passés → 3 ans à venir.
#   2. Pays identifiés par code ISO et écrits sous le nom du site
#      (« El Salvador » était écrit « Salvador », etc.). Pays hors site ignorés.
#   3. RÉSULTATS : vérifiés élection par élection (pays + date). Avant, un pays
#      qui avait déjà UN résultat n'en recevait plus jamais d'autre.
#   4. DEUX TOURS : la date du 2nd tour est enregistrée (colonne date_tour2)
#      et aucun vainqueur n'est écrit tant que le 2nd tour n'a pas eu lieu.
#   5. Wikipedia (extraction automatique de noms dans le texte) désactivée :
#      elle produisait des faux vainqueurs (« Communist Party »…).
#   6. Type d'élection enregistré sous forme de code lu par le site
#      (p = présidentielle, l = législative, s = sénatoriale, r = référendum).
# ══════════════════════════════════════════════════════════════════

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_KEY else None

QID_BRUT = re.compile(r'^Q\d+$')

# ══════════════════════════════════════
# NOMS DE PAYS — ALIGNÉS SUR LE SITE (v2, 24/10/2026)
# Le site cherche chaque pays sous SON nom exact (« Pays-Bas », « Chine »…).
# On identifie donc le pays par son code ISO (Wikidata P297), puis on le
# traduit avec la table ci-dessous, générée à partir du site lui-même.
# Si le code manque, on se rabat sur le nom Wikidata corrigé (NOMS_PAYS).
# Un pays qui ne figure pas sur le site est ignoré (et signalé dans le journal).
# ══════════════════════════════════════
ISO_VERS_SITE = {
    "ad":"Andorre", "ae":"Emirats arabes", "af":"Afghanistan", "ag":"Antigua-et-Barbuda", "al":"Albanie", "am":"Armenie",
    "ao":"Angola", "ar":"Argentine", "as":"Samoa americaines", "at":"Autriche", "au":"Australie", "aw":"Aruba",
    "az":"Azerbaidjan", "ba":"Bosnie", "bb":"Barbade", "bd":"Bangladesh", "be":"Belgique", "bf":"Burkina Faso",
    "bg":"Bulgarie", "bh":"Bahrein", "bi":"Burundi", "bj":"Benin", "bm":"Bermudes", "bn":"Brunei",
    "bo":"Bolivie", "br":"Bresil", "bs":"Bahamas", "bt":"Bhoutan", "bw":"Botswana", "by":"Belarus",
    "bz":"Belize", "ca":"Canada", "cc":"Iles Cocos", "cd":"RD Congo", "cf":"Centrafrique", "cg":"Rep. du Congo",
    "ch":"Suisse", "ci":"Cote d'Ivoire", "ck":"Iles Cook", "cl":"Chili", "cm":"Cameroun", "cn":"Chine",
    "co":"Colombie", "cr":"Costa Rica", "cu":"Cuba", "cv":"Cap-Vert", "cw":"Curaçao", "cx":"Ile Christmas",
    "cy":"Chypre", "cz":"Tchequie", "de":"Allemagne", "dj":"Djibouti", "dk":"Danemark", "dm":"Dominique",
    "do":"Rep. dominicaine", "dz":"Algerie", "ec":"Equateur", "ee":"Estonie", "eg":"Egypte", "eh":"Sahara occidental",
    "er":"Erythree", "es":"Espagne", "et":"Ethiopie", "fi":"Finlande", "fj":"Fidji", "fk":"Iles Falkland",
    "fm":"Micronesie", "fo":"Iles Féroé", "fr":"France", "ga":"Gabon", "gb":"Royaume-Uni", "gd":"Grenade",
    "ge":"Georgie", "gf":"Guyane française", "gh":"Ghana", "gi":"Gibraltar", "gl":"Groenland", "gm":"Gambie",
    "gn":"Guinee", "gp":"Guadeloupe", "gq":"Guinee equatoriale", "gr":"Grece", "gs":"Géorgie du Sud", "gt":"Guatemala",
    "gu":"Guam", "gw":"Guinee-Bissau", "gy":"Guyana", "hk":"Hong Kong", "hm":"Ile Heard", "hn":"Honduras",
    "hr":"Croatie", "ht":"Haiti", "hu":"Hongrie", "id":"Indonesie", "ie":"Irlande", "il":"Israel",
    "im":"Ile de Man", "in":"Inde", "io":"Territoire britannique OI", "iq":"Irak", "ir":"Iran", "is":"Islande",
    "it":"Italie", "je":"Jersey", "jm":"Jamaique", "jo":"Jordanie", "jp":"Japon", "ke":"Kenya",
    "kg":"Kirghizstan", "kh":"Cambodge", "ki":"Kiribati", "km":"Comores", "kn":"Saint-Kitts", "kp":"Coree du Nord",
    "kr":"Coree du Sud", "kw":"Koweit", "ky":"Iles Caiman", "kz":"Kazakhstan", "la":"Laos", "lb":"Liban",
    "lc":"Sainte-Lucie", "li":"Liechtenstein", "lk":"Sri Lanka", "lr":"Liberia", "ls":"Lesotho", "lt":"Lituanie",
    "lu":"Luxembourg", "lv":"Lettonie", "ly":"Libye", "ma":"Maroc", "mc":"Monaco", "md":"Moldavie",
    "me":"Montenegro", "mf":"Saint-Martin", "mg":"Madagascar", "mh":"Iles Marshall", "mk":"Macedoine du Nord", "ml":"Mali",
    "mm":"Myanmar", "mn":"Mongolie", "mq":"Martinique", "mr":"Mauritanie", "mt":"Malte", "mu":"Maurice",
    "mv":"Maldives", "mw":"Malawi", "mx":"Mexique", "my":"Malaisie", "mz":"Mozambique", "na":"Namibie",
    "nc":"Nouvelle-Caledonie", "ne":"Niger", "ng":"Nigeria", "ni":"Nicaragua", "nl":"Pays-Bas", "no":"Norvege",
    "np":"Nepal", "nr":"Nauru", "nu":"Niue", "nz":"Nouvelle-Zelande", "om":"Oman", "pa":"Panama",
    "pe":"Perou", "pf":"Polynésie française", "pg":"Papouasie-NG", "ph":"Philippines", "pk":"Pakistan", "pl":"Pologne",
    "pm":"Saint-Pierre-et-Miquelon", "pr":"Puerto Rico", "pt":"Portugal", "pw":"Palau", "py":"Paraguay", "qa":"Qatar",
    "ro":"Roumanie", "rs":"Serbie", "ru":"Russie", "rw":"Rwanda", "sa":"Arabie Saoudite", "sb":"Iles Salomon",
    "sd":"Soudan", "se":"Suede", "sg":"Singapour", "sh":"Sainte-Hélène", "si":"Slovenie", "sk":"Slovaquie",
    "sl":"Sierra Leone", "sm":"Saint-Marin", "sn":"Senegal", "so":"Somalie", "sr":"Suriname", "ss":"Soudan du Sud",
    "st":"Sao Tome-et-Principe", "sv":"El Salvador", "sx":"Sint Maarten", "sy":"Syrie", "sz":"Eswatini", "tc":"Iles Turques-et-Caïques",
    "td":"Tchad", "tf":"Terres australes françaises", "tg":"Togo", "th":"Thailande", "tj":"Tadjikistan", "tk":"Tokelau",
    "tl":"Timor oriental", "tm":"Turkmenistan", "tn":"Tunisie", "to":"Tonga", "tr":"Turquie", "tt":"Trinidad & Tobago",
    "tw":"Taiwan", "tz":"Tanzanie", "ua":"Ukraine", "ug":"Ouganda", "um":"Iles mineures éloignées", "us":"Etats-Unis",
    "uy":"Uruguay", "uz":"Ouzbekistan", "vc":"Saint-Vincent", "ve":"Venezuela", "vg":"Iles Vierges britanniques", "vi":"Iles Vierges américaines",
    "vn":"Vietnam", "vu":"Vanuatu", "wf":"Wallis-et-Futuna", "ws":"Samoa", "xk":"Kosovo", "ye":"Yemen",
    "yt":"Mayotte", "za":"Afrique du Sud", "zm":"Zambie", "zw":"Zimbabwe",
}
NOMS_SITE = set(ISO_VERS_SITE.values()) | {"Somaliland"}

# États dont Wikidata range le code ISO sur une autre fiche (royaumes « constitutifs »)
QID_VERS_SITE = {"Q29999": "Pays-Bas", "Q756617": "Danemark"}

NOMS_PAYS = {
    "Algérie":"Algerie","Arménie":"Armenie","Bélarus":"Belarus","Biélorussie":"Belarus",
    "Bénin":"Benin","Brésil":"Bresil","Corée du Sud":"Coree du Sud","République de Corée":"Coree du Sud",
    "Corée du Nord":"Coree du Nord","Côte d'Ivoire":"Cote d'Ivoire","Érythrée":"Erythree",
    "Éthiopie":"Ethiopie","Équateur":"Equateur","Fédération de Russie":"Russie","Géorgie":"Georgie",
    "Grèce":"Grece","Guinée":"Guinee","Guinée-Bissau":"Guinee-Bissau","Guinée équatoriale":"Guinee equatoriale",
    "Haïti":"Haiti","Îles Marshall":"Iles Marshall","Îles Salomon":"Iles Salomon","Indonésie":"Indonesie",
    "Israël":"Israel","Jamaïque":"Jamaique","Macédoine du Nord":"Macedoine du Nord","Monténégro":"Montenegro",
    "Népal":"Nepal","Nigéria":"Nigeria","Norvège":"Norvege","Nouvelle-Zélande":"Nouvelle-Zelande",
    "Ouzbékistan":"Ouzbekistan","Papouasie-Nouvelle-Guinée":"Papouasie-NG","Pérou":"Perou",
    "République centrafricaine":"Centrafrique","République démocratique du Congo":"RD Congo",
    "république démocratique du Congo":"RD Congo","République dominicaine":"Rep. dominicaine",
    "République du Congo":"Rep. du Congo","São Tomé-et-Príncipe":"Sao Tome-et-Principe",
    "Sao Tomé-et-Principe":"Sao Tome-et-Principe","Sénégal":"Senegal","Slovénie":"Slovenie","Suède":"Suede",
    "Taïwan":"Taiwan","Tchéquie":"Tchequie","Thaïlande":"Thailande","Trinité-et-Tobago":"Trinidad & Tobago",
    "Turkménistan":"Turkmenistan","Viêt Nam":"Vietnam","Yémen":"Yemen","États-Unis":"Etats-Unis",
    "Émirats arabes unis":"Emirats arabes","Arabie saoudite":"Arabie Saoudite","Azerbaïdjan":"Azerbaidjan",
    "Bahreïn":"Bahrein","Birmanie":"Myanmar","Bosnie-Herzégovine":"Bosnie","Égypte":"Egypte",
    "États fédérés de Micronésie":"Micronesie","Kirghizistan":"Kirghizstan","Koweït":"Koweit",
    "Palaos":"Palau","république populaire de Chine":"Chine","République populaire de Chine":"Chine",
    "Royaume de Danemark":"Danemark","Royaume des Pays-Bas":"Pays-Bas",
    "Saint-Christophe-et-Niévès":"Saint-Kitts","Saint-Vincent-et-les-Grenadines":"Saint-Vincent",
    "Salvador":"El Salvador","Tanzanie":"Tanzanie",
}

def pays_site(label, iso="", qid=""):
    """Renvoie le nom du pays tel que le site l'utilise, ou None si le pays
    n'est pas sur le site."""
    if qid and qid in QID_VERS_SITE:
        return QID_VERS_SITE[qid]
    if iso and iso.lower() in ISO_VERS_SITE:
        return ISO_VERS_SITE[iso.lower()]
    nom = NOMS_PAYS.get(label, label)
    return nom if nom in NOMS_SITE else None

# ══════════════════════════════════════
# RÉSULTATS VÉRIFIÉS À LA MAIN (pays, date exacte de l'élection dans Supabase)
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
    "El Salvador":        ("Nayib Bukele","Nuevas Ideas (populiste)","2026-03-01"),
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
# FILTRES (inchangés)
# ══════════════════════════════════════
TYPES_PARTIELLES = ["Q15284", "Q1198521", "Q82673"]

MOTS_CLES_REGIONAL = [
    "regional","régional","state election","provincial","gubernatorial",
    "governor","land election","landtag","cantonal","municipal","local election",
    "municipale","cantonale","départementale","state legislature","assembly election (state)",
    "county","state senate","state house","by-election (state)","legislative assembly of",
    "mairie","communale","assemblée d'","assemblée de","assemblée régionale",
    "conseil régional","regional council","conseil départemental","parlement régional",
]

MOTS_CLES_NON_POLITIQUE = [
    "club"," fc "," cf ","football","soccer","fédération sportive","sports federation",
    "société","company","corporation","société anonyme","chamber of commerce",
    "chambre de commerce","association","committee","comité","board of directors",
    "conseil d'administration","fondation","foundation","syndicat","trade union",
    "trustee","cooperative","coopérative","church","église","university senate",
    "sénat universitaire","student union","syndicat étudiant","charity","organisation caritative",
    "à la direction","leadership election","direction du parti","party leadership",
    "primaire","primary election","congrès du parti","party congress",
    "chairmanship","chairperson election","secrétaire général du parti",
]

def code_type(libelle):
    """Traduit le libellé Wikidata du type d'élection en code lu par le site."""
    t = libelle.lower()
    if "présidenti" in t or "presidential" in t: return "p"
    if "sénat" in t or "senat" in t: return "s"
    if "référendum" in t or "referendum" in t: return "r"
    if any(k in t for k in ["municipal", "local", "régional", "regional", "provincial", "state", "cantonal"]): return "m"
    return "l"

# ══════════════════════════════════════
# REQUÊTES WIKIDATA
# ══════════════════════════════════════
def requete_decouverte():
    debut = (date.today() - timedelta(days=90)).isoformat()
    fin = (date.today() + timedelta(days=3 * 366)).isoformat()
    return f"""
SELECT DISTINCT ?paysLabel ?iso ?date ?datePrecision ?typeLabel ?type WHERE {{
  ?election wdt:P31 ?type .
  ?type wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  OPTIONAL {{ ?pays wdt:P297 ?iso . }}
  ?election p:P585 ?dateStatement .
  ?dateStatement psv:P585 ?dateNode .
  ?dateNode wikibase:timeValue ?date .
  ?dateNode wikibase:timePrecision ?datePrecision .
  FILTER(?date >= "{debut}T00:00:00Z"^^xsd:dateTime)
  FILTER(?date <= "{fin}T00:00:00Z"^^xsd:dateTime)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}}
ORDER BY ?date
LIMIT 3000
"""

def requete_resultats():
    debut = (date.today() - timedelta(days=400)).isoformat()
    return f"""
SELECT ?paysLabel ?iso ?date ?vainqueurLabel ?partiLabel WHERE {{
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  OPTIONAL {{ ?pays wdt:P297 ?iso . }}
  ?election wdt:P585 ?date .
  ?election wdt:P991 ?vainqueur .
  OPTIONAL {{ ?vainqueur wdt:P102 ?parti . }}
  FILTER(?date >= "{debut}T00:00:00Z"^^xsd:dateTime)
  FILTER(?date <= NOW())
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}}
ORDER BY DESC(?date)
LIMIT 1000
"""

def requete_resultats_votes():
    debut = (date.today() - timedelta(days=400)).isoformat()
    return f"""
SELECT ?paysLabel ?iso ?date ?candLabel ?votes ?partiLabel WHERE {{
  ?election wdt:P31/wdt:P279* wd:Q40231 .
  ?election wdt:P17 ?pays .
  OPTIONAL {{ ?pays wdt:P297 ?iso . }}
  ?election wdt:P585 ?date .
  ?election p:P726 ?candStatement .
  ?candStatement ps:P726 ?cand .
  ?candStatement pq:P1111 ?votes .
  OPTIONAL {{ ?cand wdt:P102 ?parti . }}
  FILTER(?date >= "{debut}T00:00:00Z"^^xsd:dateTime)
  FILTER(?date <= NOW())
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
}}
ORDER BY DESC(?date)
LIMIT 3000
"""

def wikidata_query(query, label=""):
    for essai in range(2):
        try:
            r = requests.get(
                "https://query.wikidata.org/sparql",
                params={"query": query, "format": "json"},
                headers={"Accept": "application/json", "User-Agent": "Geolandar/6.0 (geolandar.fr)"},
                timeout=120
            )
            r.raise_for_status()
            data = r.json()["results"]["bindings"]
            print(f"  Wikidata {label}: {len(data)} résultats")
            return data
        except Exception as e:
            print(f"  Wikidata erreur {label} (essai {essai + 1}): {type(e).__name__}")
            time.sleep(10)
    return []

def v(row, cle):
    return row.get(cle, {}).get("value", "")

# ══════════════════════════════════════
# DÉCOUVERTE
# ══════════════════════════════════════
def lire_decouverte(data):
    """Transforme les lignes Wikidata en élections à enregistrer (liste de dict)."""
    elections, ignorees, hors_site = {}, 0, set()
    for row in data:
        label_pays = v(row, "paysLabel")
        pays = pays_site(label_pays, v(row, "iso"))
        date_brute = v(row, "date")[:10]
        type_qid = v(row, "type").split("/")[-1]
        type_label = v(row, "typeLabel")
        try:
            precision = int(v(row, "datePrecision") or "0")
        except ValueError:
            precision = 0
        if not pays:
            if label_pays: hors_site.add(label_pays)
            ignorees += 1; continue
        if not date_brute or not type_label or QID_BRUT.match(type_label.strip()):
            ignorees += 1; continue
        tl = type_label.lower()
        if any(k in tl for k in MOTS_CLES_NON_POLITIQUE):
            ignorees += 1; continue
        if tl.strip() in ("élection", "election", "elections", "élections"):
            ignorees += 1; continue
        annee, mois, jour = date_brute[:4], date_brute[5:7], date_brute[8:10]
        if precision >= 11:   date_el, cert = f"{annee}-{mois}-{jour}", 1
        elif precision == 10: date_el, cert = f"{annee}-{mois}-00", 2
        elif precision == 9:  date_el, cert = f"{annee}-00-00", 3
        else:
            ignorees += 1; continue
        partielle = type_qid in TYPES_PARTIELLES or any(k in tl for k in ["partielle", "by-election", "partiel", "complementaire"])
        niveau = "regionale" if (partielle or any(k in tl for k in MOTS_CLES_REGIONAL)) else "national"
        cle = (pays, date_el)
        # Une même élection peut sortir plusieurs fois (plusieurs types) : on garde le plus précis
        # présidentielle et législatives le même jour : on garde la présidentielle
        if cle not in elections or (elections[cle]["niveau"] == "regionale" and niveau == "national") \
           or (niveau == "national" and elections[cle]["type"] != "p" and code_type(type_label) == "p"):
            elections[cle] = {"pays": pays, "date": date_el, "cert": cert, "type": code_type(type_label),
                              "libelle": type_label, "niveau": niveau, "partielle": partielle}
    if hors_site:
        print(f"  ℹ Pays/territoires hors site ignorés : {', '.join(sorted(hors_site)[:30])}{'…' if len(hors_site) > 30 else ''}")
    return list(elections.values()), ignorees

def deux_tours(elections):
    """Présidentielles d'un même pays espacées de 7 à 60 jours = 1er et 2nd tour.
    Renvoie {(pays, date_tour1): date_tour2}."""
    pres = sorted((e for e in elections if e["type"] == "p" and e["niveau"] == "national" and e["cert"] == 1),
                  key=lambda e: (e["pays"], e["date"]))
    paires = {}
    for a, b in zip(pres, pres[1:]):
        if a["pays"] != b["pays"]: continue
        ecart = (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days
        if 7 <= ecart <= 60:
            paires[(a["pays"], a["date"])] = b["date"]
    return paires

def decouvrir_elections():
    data = wikidata_query(requete_decouverte(), "découverte")
    elections, ignorees = lire_decouverte(data)
    nouvelles = 0
    for e in elections:
        try:
            res = supabase.table("elections").select("id").eq("pays", e["pays"]).eq("date", e["date"]).execute()
            if res.data: continue
            supabase.table("elections").insert({
                "pays": e["pays"], "date": e["date"], "winner": "", "party": "", "done": False,
                "type": e["type"], "cert": e["cert"], "niveau": e["niveau"],
                "updated_at": datetime.now().isoformat()
            }).execute()
            marque = (" [PARTIELLE]" if e["partielle"] else "") + (" [RÉGIONALE]" if e["niveau"] == "regionale" else "")
            print(f"  + {e['pays']} ({e['date']}) {e['libelle']}{marque}")
            nouvelles += 1
        except Exception as ex:
            print(f"  ✗ insertion {e['pays']} {e['date']}: {ex}")
    print(f"  {nouvelles} nouvelles élections ajoutées, {ignorees} lignes ignorées")
    # Seconds tours
    for (pays, d1), d2 in deux_tours(elections).items():
        try:
            supabase.table("elections").update({"date_tour2": d2}).eq("pays", pays).eq("date", d1).execute()
            print(f"  🔁 {pays} : 1er tour {d1}, 2nd tour {d2}")
        except Exception as ex:
            print(f"  ⚠ {pays} : impossible d'écrire le 2nd tour ({ex}). La colonne date_tour2 existe-t-elle ? (fichier geolandar_second_tour.sql)")
    return elections

# ══════════════════════════════════════
# RÉSULTATS
# ══════════════════════════════════════
def lire_resultats(data):
    """{(pays, date): {winner, party}} — vainqueur déclaré sur Wikidata (P991)."""
    out = {}
    for row in data:
        pays = pays_site(v(row, "paysLabel"), v(row, "iso"))
        winner, party, d = v(row, "vainqueurLabel"), v(row, "partiLabel"), v(row, "date")[:10]
        if not pays or not winner or winner == "undefined" or QID_BRUT.match(winner.strip()) or not d:
            continue
        if party and QID_BRUT.match(party.strip()): party = ""
        out.setdefault((pays, d), {"winner": winner, "party": party})
    return out

def lire_resultats_votes(data):
    """{(pays, date): {winner, party}} — candidat ayant reçu le plus de voix."""
    meilleur = {}
    for row in data:
        pays = pays_site(v(row, "paysLabel"), v(row, "iso"))
        d, cand, parti = v(row, "date")[:10], v(row, "candLabel"), v(row, "partiLabel")
        if not pays or not cand or not d or QID_BRUT.match(cand.strip()): continue
        try: votes = float(v(row, "votes"))
        except ValueError: continue
        if parti and QID_BRUT.match(parti.strip()): parti = ""
        cle = (pays, d)
        if cle not in meilleur or votes > meilleur[cle]["votes"]:
            meilleur[cle] = {"winner": cand, "party": parti, "votes": votes}
    return meilleur

def lignes_sans_resultat():
    """Élections passées (date exacte) sans vainqueur, avec leur éventuel 2nd tour."""
    today = date.today().isoformat()
    lignes = {}
    try:
        # pas encore de résultat, ou marquée terminée mais sans vainqueur
        for q in (supabase.table("elections").select("*").eq("done", False).lte("date", today),
                  supabase.table("elections").select("*").eq("done", True).eq("winner", "").lte("date", today)):
            for r in q.execute().data:
                lignes[r["id"]] = r
    except Exception as ex:
        print(f"  ✗ lecture Supabase: {ex}")
        return []
    return [r for r in lignes.values() if r.get("pays") and r.get("date") and "-00" not in r["date"]]

def save(row, winner, party, source):
    """Met à jour UNE élection déjà découverte. Refuse si le 2nd tour n'a pas eu lieu."""
    t2 = row.get("date_tour2")
    if t2 and t2 > date.today().isoformat():
        print(f"  ⏸ {row['pays']} ({row['date']}) : 2nd tour le {t2}, pas de vainqueur avant — ignoré ({source})")
        return False
    try:
        supabase.table("elections").update({
            "winner": winner, "party": party, "done": True, "updated_at": datetime.now().isoformat()
        }).eq("id", row["id"]).execute()
        print(f"  ✓ {row['pays']} ({row['date']}) : {winner} ({source})")
        return True
    except Exception as ex:
        print(f"  ✗ {row['pays']}: {ex}")
        return False

def chercher_resultat(row, sources):
    """Cherche un vainqueur pour l'élection (date du 2nd tour en priorité)."""
    dates = [d for d in (row.get("date_tour2"), row["date"]) if d]
    for nom_source, table in sources:
        for d in dates:
            r = table.get((row["pays"], d))
            if r: return r, nom_source
    return None, None

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def main():
    print("=" * 55)
    print("  GEOLANDAR — Mise à jour automatique v6.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)

    if supabase is None:
        print("  (pas de clé Supabase : essai à blanc de la découverte, rien n'est écrit)")
        elections, ign = lire_decouverte(wikidata_query(requete_decouverte(), "découverte"))
        for e in sorted(elections, key=lambda e: e["date"]):
            if e["niveau"] == "national": print(f"   {e['date']} {e['pays']} [{e['type']}] {e['libelle']}")
        print(f"  2nd tours détectés : {deux_tours(elections)}")
        return

    print("\n[1] Découverte des élections (90 jours passés → 3 ans à venir)...")
    decouvrir_elections()
    time.sleep(3)

    print("\n[2] Résultats — sources Wikidata...")
    connus = {(p, d): {"winner": w, "party": pa} for p, (w, pa, d) in RESULTATS_CONNUS.items()}
    directs = lire_resultats(wikidata_query(requete_resultats(), "vainqueurs déclarés"))
    time.sleep(2)
    votes = lire_resultats_votes(wikidata_query(requete_resultats_votes(), "vainqueurs par nombre de voix"))
    sources = [("Manuel", connus), ("Wikidata", directs), ("Wikidata-votes", votes)]

    print("\n[3] Élections passées sans résultat...")
    total, manquants = 0, []
    for row in lignes_sans_resultat():
        r, src = chercher_resultat(row, sources)
        if r:
            if save(row, r["winner"], r["party"], src): total += 1
        elif row.get("niveau") == "national":
            manquants.append(f"{row['pays']} ({row['date']})")
    if manquants:
        print(f"\n  📋 {len(manquants)} élections nationales passées toujours sans résultat (à compléter dans RESULTATS_CONNUS si besoin) :")
        for m in sorted(manquants): print(f"     - {m}")

    print(f"\n{'=' * 55}\n  TOTAL: {total} résultats enregistrés\n  Terminé: {datetime.now().strftime('%H:%M:%S')}\n{'=' * 55}")

if __name__ == "__main__":
    main()
