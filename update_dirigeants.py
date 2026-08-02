import requests
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
]

def deduire_position(libelles_ideologie, nom_parti):
    """Déduit un score -10/+10 à partir des libellés d'idéologie Wikidata,
    ou à défaut du nom du parti."""
    textes = [t.lower() for t in libelles_ideologie if t] + [(nom_parti or "").lower()]
    for texte in textes:
        for mot, score in MOTS_CLES_POSITION:
            if mot in texte:
                return score
    return 0

# ══════════════════════════════════════
# REQUÊTE WIKIDATA — chef d'État (P35) et chef de gouvernement (P6)
# de tous les pays, avec parti (P102) et date de prise de fonction (P580)
# ══════════════════════════════════════
QUERY_DIRIGEANTS = """
SELECT ?paysLabel
       ?hos ?hosLabel ?hosPartyLabel ?hosStart
       ?hog ?hogLabel ?hogPartyLabel ?hogStart
WHERE {
  ?pays wdt:P31 wd:Q3624078.
  OPTIONAL {
    ?pays p:P35 ?hosStmt.
    ?hosStmt ps:P35 ?hos.
    FILTER NOT EXISTS { ?hosStmt pq:P582 ?hosEnd. }
    OPTIONAL { ?hosStmt pq:P580 ?hosStart. }
    OPTIONAL { ?hos wdt:P102 ?hosPartyItem. ?hosPartyItem rdfs:label ?hosPartyLabel. FILTER(LANG(?hosPartyLabel)="fr"). }
  }
  OPTIONAL {
    ?pays p:P6 ?hogStmt.
    ?hogStmt ps:P6 ?hog.
    FILTER NOT EXISTS { ?hogStmt pq:P582 ?hogEnd. }
    OPTIONAL { ?hogStmt pq:P580 ?hogStart. }
    OPTIONAL { ?hog wdt:P102 ?hogPartyItem. ?hogPartyItem rdfs:label ?hogPartyLabel. FILTER(LANG(?hogPartyLabel)="fr"). }
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
            }

        hog_nom = ligne.get("hogLabel", {}).get("value", "")
        if hog_nom and ligne.get("hog"):
            entree["hog"].add(hog_nom)
            entree["data"].setdefault("hog_info", {})[hog_nom] = {
                "parti": ligne.get("hogPartyLabel", {}).get("value", ""),
                "start": ligne.get("hogStart", {}).get("value", ""),
            }

    resultats = {}
    for pays, entree in par_pays.items():
        role = "hos" if pays in PAYS_HOS else "hog"
        noms = entree["hos"] if role == "hos" else entree["hog"]
        info_key = "hos_info" if role == "hos" else "hog_info"
        infos = entree["data"].get(info_key, {})

        if not noms:
            continue

        # Fiabilité : plusieurs "titulaires actuels" en même temps sur
        # Wikidata = donnée ambiguë (transition, conflit de succession...)
        ambigu = len(noms) > 1
        nom = sorted(noms)[0]  # à défaut de mieux, le premier par ordre alphabétique
        info = infos.get(nom, {})
        parti = info.get("parti", "")
        date_debut = fmt_date(info.get("start", ""))

        titre = "Chef d'État" if role == "hos" else "Chef du gouvernement"
        position = deduire_position([], parti)

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
