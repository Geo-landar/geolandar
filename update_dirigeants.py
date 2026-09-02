import requests
import re
QID_BRUT = re.compile(r'^Q\d+$')
from supabase import create_client
from datetime import datetime, date
import os
import time

# ══════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://tmbupyyugedmtmvzadeq.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════
# NORMALISATION DES NOMS DE PAYS
# (mêmes conventions que E[]/PAYS[]/LEADERS dans index.html)
# ══════════════════════════════════════
NOMS_PAYS = {
    "Algérie": "Algerie", "Arménie": "Armenie", "Bélarus": "Belarus",
    "Bénin": "Benin", "Brésil": "Bresil", "Corée du Sud": "Coree du Sud",
    "Corée du Nord": "Coree du Nord", "Côte d'Ivoire": "Cote d'Ivoire",
    "Érythrée": "Erythree", "Éthiopie": "Ethiopie", "Équateur": "Equateur",
    "Fédération de Russie": "Russie", "Géorgie": "Georgie", "Grèce": "Grece",
    "Guinée": "Guinee", "Guinée-Bissau": "Guinee-Bissau",
    "Guinée équatoriale": "Guinee equatoriale", "Haïti": "Haiti",
    "Indonésie": "Indonesie", "Israël": "Israel", "Jamaïque": "Jamaique",
    "Macédoine du Nord": "Macedoine du Nord", "Monténégro": "Montenegro",
    "Mozambique": "Mozambique", "Népal": "Nepal", "Nigéria": "Nigeria",
    "Norvège": "Norvege", "Nouvelle-Zélande": "Nouvelle-Zelande",
    "Ouzbékistan": "Ouzbekistan", "Papouasie-Nouvelle-Guinée": "Papouasie-NG",
    "Pérou": "Perou", "République centrafricaine": "Centrafrique",
    "République démocratique du Congo": "RD Congo",
    "République dominicaine": "Rep. dominicaine",
    "République du Congo": "Rep. du Congo",
    "São Tomé-et-Príncipe": "Sao Tome-et-Principe",
    "Sénégal": "Senegal", "Slovénie": "Slovenie",
    "Sri Lanka": "Sri Lanka", "Suède": "Suede",
    "Tchéquie": "Tchequie", "Thaïlande": "Thailande",
    "Trinité-et-Tobago": "Trinidad & Tobago",
    "Turkménistan": "Turkmenistan",
    "Viêt Nam": "Vietnam", "Yémen": "Yemen", "États-Unis": "Etats-Unis",
    "Émirats arabes unis": "Emirats arabes", "El Salvador": "El Salvador",
}

def normaliser(pays):
    return NOMS_PAYS.get(pays, pays)

# ══════════════════════════════════════
# QUEL POSTE FAIT AUTORITÉ : chef d'État (hos) ou chef du gouvernement (hog) ?
# Par défaut : hog (systèmes parlementaires, majorité des pays).
# Liste des pays où c'est le chef d'État qui détient le pouvoir réel
# (régimes présidentiels ou semi-présidentiels, monarchies absolues,
# régimes autoritaires à parti unique, juntes militaires).
# ══════════════════════════════════════
PAYS_HOS = {
    "Etats-Unis","France","Russie","Turquie","Bresil","Argentine","Mexique",
    "Colombie","Chili","Perou","Equateur","Venezuela","Bolivie","Paraguay",
    "Uruguay","Costa Rica","Panama","Guatemala","Honduras","El Salvador",
    "Nicaragua","Rep. dominicaine","Cuba","Indonesie","Philippines",
    "Coree du Sud","Iran","Egypte","Nigeria","Kenya","Ghana","Ouganda",
    "Rwanda","Tanzanie","Angola","RD Congo","Cameroun","Senegal",
    "Cote d'Ivoire","Gabon","Rep. du Congo","Djibouti","Zambie","Zimbabwe",
    "Namibie","Botswana","Mali","Burkina Faso","Niger","Tchad","Guinee",
    "Mauritanie","Benin","Madagascar","Mozambique","Malawi","Somalie",
    "Soudan","Soudan du Sud","Liberia","Sierra Leone","Togo",
    "Guinee equatoriale","Centrafrique","Erythree","Burundi","Comores",
    "Cap-Vert","Sao Tome-et-Principe","Guinee-Bissau","Gambie",
    "Coree du Nord","Chine","Vietnam","Cambodge","Laos","Kazakhstan",
    "Ouzbekistan","Tadjikistan","Kirghizstan","Turkmenistan","Azerbaidjan",
    "Belarus","Ukraine","Georgie","Armenie","Mongolie","Afghanistan",
    "Yemen","Syrie","Taiwan","Chypre","Seychelles","Maldives",
    "Sri Lanka","Timor oriental","Kiribati","Nauru","Palau",
    "Iles Marshall","Micronesie",
}

# ══════════════════════════════════════
# CORRESPONDANCE PARTI -> ORIENTATION POLITIQUE (-10 à +10)
# Basée sur les mots-clés d'idéologie politique (P1387 sur Wikidata,
# ou à défaut sur le nom du parti). Défaut = 0 (centre / non déterminé).
# ══════════════════════════════════════
MOTS_CLES_POSITION = [
    ("extrême droite", 8), ("far-right", 8), ("far right", 8),
    ("extrême gauche", -8), ("far-left", -8), ("far left", -8),
    ("nationalisme", 6), ("nationalist", 6),
    ("populisme de droite", 6), ("right-wing populis", 6),
    ("conservat", 4),
    ("droite", 5), ("right-wing", 5),
    ("centre droit", 3), ("centre-right", 3),
    ("libéral", 1), ("liberal", 1),
    ("centre gauche", -2), ("centre-left", -2),
    ("social-démocrat", -3), ("social democrat", -3),
    ("socialis", -5), ("gauche", -5), ("left-wing", -5),
    ("communis", -8),
    ("vert", -1), ("green", -1), ("écologis", -1),
    ("autoritar", 7), ("authoritarian", 7),

    # ══ NOMS DE PARTIS RÉELS PAR PAYS ══
    # Les mots-clés génériques ci-dessus ne suffisent pas : la plupart des
    # partis dans le monde (ANC, UDA, BJP...) ne contiennent aucun mot
    # évoquant explicitement une tendance politique. Liste construite à
    # partir de connaissances générales sur les partis au pouvoir dans le
    # monde — fiable pour les partis bien documentés, mais non vérifiée
    # individuellement par recherche pour chacun. En cas de doute réel,
    # aucune entrée n'est ajoutée : mieux vaut "non applicable" qu'un
    # score inventé.

    # — EUROPE —
    ("rassemblement national", 8), ("renaissance", 0),  # RN=droite, Renaissance=centre (Macron)
    ("la france insoumise", -7), ("parti socialiste français", -5), ("les républicains", 4),
    ("christlich demokratische", 3), ("sozialdemokratische partei", -3), ("alternative für deutschland", 8),
    ("die grünen", -1), ("die linke", -6), ("freie demokratische", 1),
    ("conservative party", 4), ("labour party", -4), ("reform uk", 7), ("liberal democrat", 1),
    ("fratelli d'italia", 7), (" lega ", 6), ("partito democratico", -3), ("forza italia", 4),
    ("partido popular", 4), ("psoe", -4), (" vox ", 8), ("sumar", -6),
    ("prawo i sprawiedliwość", 6), ("koalicja obywatelska", 1),
    ("fidesz", 7),
    ("chega", 7), ("psd portugal", 3),
    ("vvd", 3), ("pvv", 8), ("d66", 0),
    ("moderaterna", 4), ("sverigedemokraterna", 7), ("socialdemokraterna", -4),
    ("arbeiderpartiet", -4), ("høyre", 4),
    ("socialdemokratiet", -3), ("venstre danemark", 3),
    ("kokoomus", 3), ("sdp finlande", -3),
    ("fianna fáil", 1), ("fine gael", 2), ("sinn féin", -4),
    ("nea dimokratia", 4), ("new democracy grèce", 4), ("syriza", -6),
    ("adalet ve kalkınma", 5), ("akp", 5), ("chp turquie", -3),
    ("edinaïa rossia", 8), ("united russia", 8),
    ("ods tchéquie", 3), (" ano ", 0),
    ("övp", 3), ("fpö", 8), ("spö", -3),
    ("union démocratique du centre", 6), ("udc suisse", 6), ("parti socialiste suisse", -3),

    # — AMÉRIQUES —
    ("republican party", 5), ("democratic party", -3),
    ("morena", -4), ("pan mexique", 4), ("pri mexique", 0),
    ("la libertad avanza", 8), ("pro argentine", 4),
    ("frente amplio chile", -5), ("chile vamos", 3),
    ("fuerza popular", 5), ("perú libre", -6),
    ("psuv", -7), ("partido socialista unido de venezuela", -7),
    ("mas bolivie", -6), ("movimiento al socialismo", -6),
    ("partido colorado", 3), ("frente amplio uruguay", -4),
    ("nuevas ideas", 5),  # Salvador, Bukele — populisme sécuritaire droite

    # — AFRIQUE —
    ("all progressives congress", 2),
    ("mostaqbal watan", 5),
    ("prosperity party éthiopie", 2),
    ("new patriotic party", 3), ("national democratic congress", -3),
    ("pastef", -4),
    ("chama cha mapinduzi", 3),
    ("national resistance movement", 5),
    ("rwandan patriotic front", 5),
    ("zanu-pf", 6),
    ("united party for national development", 1),
    ("swapo", -3),
    ("mpla angola", -1),
    ("frelimo", -2),
    ("rassemblement national démocratique", 4),  # Algérie RND

    # — ASIE —
    ("communist party of china", -8), ("parti communiste chinois", -8),
    ("bharatiya janata party", 6), ("indian national congress", -2),
    ("jiyu-minshuto", 3), ("liberal democratic party japon", 3),
    ("people power party", 4), ("democratic party of korea", -3),
    ("gerindra", 3), ("pdi-p", -2),
    ("pakistan muslim league", 2), ("pakistan peoples party", -2), ("pakistan tehreek-e-insaf", 0),
    ("bangladesh nationalist party", 3), ("awami league", -2),
    ("communist party of vietnam", -7),
    ("pheu thai", -2),
    ("umno", 3), ("parti keadilan rakyat", -2),
    ("people's action party", 3),
    ("likud", 6), ("yesh atid", 0),

    # — OCÉANIE —
    ("liberal party of australia", 4), ("labor party australien", -3), ("nationals australie", 5),
    ("national party nouvelle-zélande", 3), ("labour party nouvelle-zélande", -3),

    # — DÉJÀ VÉRIFIÉES INDIVIDUELLEMENT (recherche web) —
    ("pacto histórico", -6), ("historic pact", -6),  # Colombie, Petro
    ("african national congress", -3), (" anc ", -3),  # Afrique du Sud
    ("partido dos trabalhadores", -6), ("workers' party", -6),  # Brésil, Lula
    ("congolais du travail", 7),  # Congo-Brazzaville — régime personnaliste autoritaire
    ("botswana democratic party", 3), (" bdp ", 3),  # Botswana
    ("mouvement patriotique du salut", 5), ("patriotic salvation movement", 5),  # Tchad
]

def deduire_position(libelles_ideologie, nom_parti):
    """Déduit un score -10/+10 à partir des libellés d'idéologie Wikidata,
    ou à défaut du nom du parti. Retourne None (pas 0) si aucune donnée
    n'est disponible — un régime militaire/de transition sans parti n'est
    pas "centriste", c'est juste une donnée manquante. Confondre les deux
    afficherait à tort un dirigeant autoritaire comme modéré."""
    textes = [t.lower() for t in libelles_ideologie if t] + [(nom_parti or "").lower()]
    for texte in textes:
        for mot, score in MOTS_CLES_POSITION:
            if mot in texte:
                return score
    # Aucun mot-clé trouvé : si le parti est vide ou générique (indépendant,
    # sans étiquette, transition militaire...), on ne sait vraiment rien —
    # ne pas prétendre "centre" par défaut.
    return None

# ══════════════════════════════════════
# REQUÊTE WIKIDATA — chef d'État (P35) et chef de gouvernement (P6)
# de tous les pays, avec parti (P102) et date de prise de fonction (P580)
# ══════════════════════════════════════
QUERY_DIRIGEANTS = """
SELECT ?paysLabel
       ?hos ?hosLabel ?hosPartyLabel ?hosStart ?hosIdeoLabel
       ?hog ?hogLabel ?hogPartyLabel ?hogStart ?hogIdeoLabel
WHERE {
  ?pays wdt:P31 wd:Q3624078.
  OPTIONAL {
    ?pays p:P35 ?hosStmt.
    ?hosStmt ps:P35 ?hos.
    FILTER NOT EXISTS { ?hosStmt pq:P582 ?hosEnd. }
    OPTIONAL { ?hosStmt pq:P580 ?hosStart. }
    OPTIONAL {
      ?hos wdt:P102 ?hosPartyItem. ?hosPartyItem rdfs:label ?hosPartyLabel. FILTER(LANG(?hosPartyLabel)="fr").
      OPTIONAL { ?hosPartyItem wdt:P1387 ?hosIdeoItem. ?hosIdeoItem rdfs:label ?hosIdeoLabel. FILTER(LANG(?hosIdeoLabel)="fr"). }
    }
  }
  OPTIONAL {
    ?pays p:P6 ?hogStmt.
    ?hogStmt ps:P6 ?hog.
    FILTER NOT EXISTS { ?hogStmt pq:P582 ?hogEnd. }
    OPTIONAL { ?hogStmt pq:P580 ?hogStart. }
    OPTIONAL {
      ?hog wdt:P102 ?hogPartyItem. ?hogPartyItem rdfs:label ?hogPartyLabel. FILTER(LANG(?hogPartyLabel)="fr").
      OPTIONAL { ?hogPartyItem wdt:P1387 ?hogIdeoItem. ?hogIdeoItem rdfs:label ?hogIdeoLabel. FILTER(LANG(?hogIdeoLabel)="fr"). }
    }
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
"""

def wikidata_query(query):
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/json", "User-Agent": "Geolandar-Dirigeants/1.0"},
            timeout=90
        )
        r.raise_for_status()
        return r.json()["results"]["bindings"]
    except Exception as e:
        print(f"  Erreur requête Wikidata: {type(e).__name__} — {e}")
        return []

def fmt_date(valeur_iso):
    """Formate une date ISO Wikidata (peut être vide) en JJ/MM/AAAA."""
    if not valeur_iso:
        return None
    try:
        return datetime.fromisoformat(valeur_iso.replace("Z", "")).strftime("%d/%m/%Y")
    except Exception:
        return None

def construire_dirigeants():
    """Interroge Wikidata et construit, pour chaque pays, l'entrée dirigeant
    à écrire dans Supabase. Regroupe les lignes par pays (une ligne par
    combinaison hos/hog possible dans les résultats bruts)."""
    print("  Interrogation de Wikidata (chefs d'État et de gouvernement)...")
    lignes = wikidata_query(QUERY_DIRIGEANTS)
    print(f"  {len(lignes)} lignes reçues")

    # Regrouper par pays : on garde toutes les valeurs hos et hog vues,
    # pour détecter les cas ambigus (plusieurs personnes "actuelles" à la fois)
    par_pays = {}
    for ligne in lignes:
        pays = normaliser(ligne.get("paysLabel", {}).get("value", ""))
        if not pays:
            continue
        entree = par_pays.setdefault(pays, {"hos": set(), "hog": set(), "data": {}})

        hos_nom = ligne.get("hosLabel", {}).get("value", "")
        if hos_nom and ligne.get("hos"):
            entree["hos"].add(hos_nom)
            entree["data"].setdefault("hos_info", {})[hos_nom] = {
                "parti": ligne.get("hosPartyLabel", {}).get("value", ""),
                "start": ligne.get("hosStart", {}).get("value", ""),
                "ideologie": ligne.get("hosIdeoLabel", {}).get("value", ""),
            }

        hog_nom = ligne.get("hogLabel", {}).get("value", "")
        if hog_nom and ligne.get("hog"):
            entree["hog"].add(hog_nom)
            entree["data"].setdefault("hog_info", {})[hog_nom] = {
                "parti": ligne.get("hogPartyLabel", {}).get("value", ""),
                "start": ligne.get("hogStart", {}).get("value", ""),
                "ideologie": ligne.get("hogIdeoLabel", {}).get("value", ""),
            }

    resultats = {}
    for pays, entree in par_pays.items():
        role = "hos" if pays in PAYS_HOS else "hog"
        noms = entree["hos"] if role == "hos" else entree["hog"]
        info_key = "hos_info" if role == "hos" else "hog_info"
        infos = entree["data"].get(info_key, {})

        if not noms:
            continue

        # GARDE-FOU : rejeter les noms qui sont un identifiant Wikidata brut
        # (ex: "Q3052772") plutôt qu'un vrai nom traduit — même correctif que
        # celui déjà appliqué à update_elections.py, oublié ici par erreur.
        infos_par_nom = entree["data"].get(info_key, {})
        noms_valides = [n for n in noms if not QID_BRUT.match(n.strip())]
        if not noms_valides:
            continue  # aucun nom exploitable pour ce pays, on l'ignore

        # Fiabilité : plusieurs "titulaires actuels" en même temps sur
        # Wikidata = donnée ambiguë (transition, conflit de succession...)
        ambigu = len(noms_valides) > 1

        # CORRECTIF : en cas d'ambiguïté, choisir le titulaire dont la date
        # de prise de fonction (P580) est la plus RÉCENTE, pas le premier
        # par ordre alphabétique. Un ordre alphabétique pouvait faire
        # remonter un ancien dirigeant dans les pays à forte rotation
        # politique (ex: plusieurs Premiers ministres en quelques années),
        # quand l'ancien titulaire n'a pas de date de fin correctement
        # renseignée sur Wikidata.
        def cle_tri(n):
            d = infos_par_nom.get(n, {}).get("start", "")
            return d or ""  # chaîne vide = trié en premier (le plus ancien)
        nom = sorted(noms_valides, key=cle_tri, reverse=True)[0] if ambigu else noms_valides[0]
        info = infos_par_nom.get(nom, {})
        parti = info.get("parti", "")
        ideologie = info.get("ideologie", "")
        date_debut = fmt_date(info.get("start", ""))

        titre = "Chef d'État" if role == "hos" else "Chef du gouvernement"
        position = deduire_position([ideologie] if ideologie else [], parti)

        if ambigu:
            fiabilite = 4  # non reconnu / conflit — plusieurs titulaires détectés
        elif not date_debut:
            fiabilite = 3  # partiellement reconnu — date de prise de fonction inconnue
        else:
            fiabilite = 1  # certifié

        description = (
            f"{nom}, {titre.lower()} depuis le {date_debut}." if date_debut
            else f"{nom}, {titre.lower()} (date de prise de fonction non renseignée sur Wikidata)."
        )
        if parti:
            description += f" Parti : {parti}."
        if ambigu:
            description += " ⚠️ Plusieurs titulaires actuels détectés sur Wikidata — à vérifier."

        resultats[pays] = {
            "pays": pays,
            "nom": nom,
            "titre": titre,
            "parti": parti,
            "position": position,
            "description": description,
            "fiabilite": fiabilite,
        }

    return resultats

def sauvegarder(dirigeants):
    total = 0
    for pays, d in dirigeants.items():
        try:
            supabase.table("dirigeants").upsert({
                "pays": d["pays"],
                "nom": d["nom"],
                "titre": d["titre"],
                "parti": d["parti"],
                "position": d["position"],
                "description": d["description"],
                "fiabilite": d["fiabilite"],
                "updated_at": datetime.now().isoformat(),
            }, on_conflict="pays").execute()
            total += 1
        except Exception as e:
            print(f"  ✗ {pays}: {e}")
    return total

# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def main():
    print("=" * 60)
    print("  GEOLANDAR — Mise à jour automatique des dirigeants v1.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    dirigeants = construire_dirigeants()
    print(f"\n  {len(dirigeants)} pays avec un dirigeant identifié")

    print("\n  Écriture dans Supabase...")
    total = sauvegarder(dirigeants)

    # Récapitulatif des cas à surveiller (visible directement dans les logs)
    ambigus = [p for p, d in dirigeants.items() if d["fiabilite"] == 4]
    incertains = [p for p, d in dirigeants.items() if d["fiabilite"] == 3]
    if ambigus:
        print(f"\n  ⚠️  {len(ambigus)} pays avec plusieurs titulaires détectés (à vérifier) :")
        for p in ambigus:
            print(f"     - {p}")
    if incertains:
        print(f"\n  🟠 {len(incertains)} pays sans date de prise de fonction connue :")
        for p in incertains:
            print(f"     - {p}")

    print(f"\n{'=' * 60}")
    print(f"  TOTAL: {total} dirigeants mis à jour")
    print(f"  Terminé: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
