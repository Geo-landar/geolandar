import requests
import re
from supabase import create_client
from datetime import datetime, date
import os
import time

# ══════════════════════════════════════════════════════════════════
#  GEOLANDAR — Mise à jour automatique des dirigeants — v2.0 (24/10/2026)
#  Corrections par rapport à la v1 :
#   1. Chaque dirigeant est écrit sous le nom de pays UTILISÉ PAR LE SITE
#      (identification par code ISO). Avant, une vingtaine de pays étaient
#      écrits sous le nom Wikidata (« Royaume des Pays-Bas »…) et le site
#      ne les voyait jamais (ex. Pays-Bas bloqué sur Dick Schoof).
#   2. Liste corrigée des pays où le pouvoir réel est au chef de l'État
#      (Arménie, Géorgie, Mongolie, Cambodge… affichaient la mauvaise personne).
#   3. Wikidata : les déclarations « obsolètes » sont ignorées, la déclaration
#      « préférée » l'emporte en cas de doute.
#   4. Corrections manuelles conditionnelles quand Wikidata est en retard
#      (ex. Népal) : elles ne s'appliquent QUE tant que Wikidata renvoie encore
#      l'ancien nom, puis se désactivent toutes seules.
#   5. Pays absents du site, collèges (Suisse, Saint-Marin) : jamais écrits.
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
# QUEL POSTE AFFICHER : chef d'État (hos) ou chef du gouvernement (hog) ?
# Par défaut : chef du gouvernement (régimes parlementaires).
# Ici : pays où le pouvoir réel appartient au chef de l'État.
# Retirés le 24/10 : Arménie, Géorgie, Mongolie, Cambodge, Togo (le Premier
# ministre / président du Conseil y détient le pouvoir).
# Ajoutés : Algérie, Guyana, Tunisie, Suriname, Myanmar, Monaco, Vatican,
# Qatar, Émirats, Koweït, Eswatini.
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
    "Soudan","Soudan du Sud","Liberia","Sierra Leone",
    "Guinee equatoriale","Centrafrique","Erythree","Burundi","Comores",
    "Cap-Vert","Sao Tome-et-Principe","Guinee-Bissau","Gambie",
    "Coree du Nord","Chine","Vietnam","Laos","Kazakhstan",
    "Ouzbekistan","Tadjikistan","Kirghizstan","Turkmenistan","Azerbaidjan",
    "Belarus","Ukraine","Afghanistan",
    "Yemen","Syrie","Taiwan","Chypre","Seychelles","Maldives",
    "Sri Lanka","Timor oriental","Kiribati","Nauru","Palau",
    "Iles Marshall","Micronesie",
    # ajoutés le 24/10/2026
    "Algerie","Guyana","Tunisie","Suriname","Myanmar","Monaco","Vatican",
    "Qatar","Emirats arabes","Koweit","Eswatini",
}

# Pays que le script ne doit jamais écrire : gouvernement collégial (pas
# une personne) ou cas suivis à la main dans le site.
PAYS_IGNORES = {"Suisse", "Saint-Marin", "Arabie Saoudite", "Bosnie"}

# ══════════════════════════════════════
# CORRECTIONS QUAND WIKIDATA EST EN RETARD
# « si_wikidata » = ancien(s) nom(s) encore renvoyé(s) à tort par Wikidata.
# La correction ne s'applique que dans ce cas : dès que Wikidata renvoie
# quelqu'un d'autre (le bon titulaire ou un successeur), elle est ignorée.
# Vérifié le 10/10/2026 (voir le document « points à corriger »).
# ══════════════════════════════════════
CORRECTIONS = {
    "Nepal":        {"si_wikidata": ["Pushpa Kamal Dahal", "Sushila Karki", "Khadga Prasad Sharma Oli"],
                     "nom": "Balen Shah", "titre": "Premier ministre", "depuis": "27/03/2026"},
    "Thailande":    {"si_wikidata": ["Phumtham Wechayachai", "Paetongtarn Shinawatra"],
                     "nom": "Anutin Charnvirakul", "titre": "Premier ministre", "depuis": "septembre 2025"},
    "Malawi":       {"si_wikidata": ["Lazarus Chakwera"],
                     "nom": "Peter Mutharika", "titre": "Président", "depuis": "octobre 2025"},
    "Samoa":        {"si_wikidata": ["Naomi Mataʻafa", "Fiamē Naomi Mataʻafa", "Naomi Mata'afa"],
                     "nom": "La'auli Leuatea Schmidt", "titre": "Premier ministre", "depuis": "septembre 2025"},
    "Vanuatu":      {"si_wikidata": ["Bob Loughman", "Charlot Salwai"],
                     "nom": "Jotham Napat", "titre": "Premier ministre", "depuis": "février 2025"},
    "Maurice":      {"si_wikidata": ["Pravind Jugnauth"],
                     "nom": "Navin Ramgoolam", "titre": "Premier ministre", "depuis": "novembre 2024"},
    "Irak":         {"si_wikidata": ["Mohammed Chia al-Soudani", "Mohammed Shia' Al Sudani"],
                     "nom": "Ali al-Zaidi", "titre": "Premier ministre", "depuis": "mai 2026"},
    "Iles Salomon": {"si_wikidata": ["Jeremiah Manele"],
                     "nom": "Matthew Wale", "titre": "Premier ministre", "depuis": "15/05/2026"},
    "Madagascar":   {"si_wikidata": ["Andry Rajoelina", "Christian Ntsay"],
                     "nom": "Michael Randrianirina", "titre": "Président de la Refondation (colonel)", "depuis": "octobre 2025"},
    "Guinee-Bissau":{"si_wikidata": ["Umaro Sissoco Embaló"],
                     "nom": "Horta N'Tam", "titre": "Président de la transition (général)", "depuis": "novembre 2025"},
}

# ══════════════════════════════════════
# CORRESPONDANCE PARTI -> ORIENTATION POLITIQUE (-10 à +10) — inchangée
# ══════════════════════════════════════
MOTS_CLES_POSITION = [
    # ══ NOMS DE PARTIS RÉELS — VÉRIFIÉS EN PRIORITÉ ══
    # Ces correspondances précises passent AVANT les mots-clés génériques
    # plus bas : certains partis (le "PSD" portugais par exemple, dont le
    # nom complet contient "social democrata") matcheraient sinon à tort un
    # mot-clé générique avant d'atteindre leur véritable classification.
    # Liste construite à partir de connaissances générales sur les partis
    # au pouvoir dans le monde — fiable pour les partis bien documentés,
    # mais non vérifiée individuellement par recherche pour chacun. En cas
    # de doute réel, aucune entrée n'est ajoutée : mieux vaut "non
    # applicable" qu'un score inventé.

    # — EUROPE —
    ("rassemblement national", 8), ("renaissance", 0),  # RN=droite, Renaissance=centre (Macron)
    ("la france insoumise", -7), ("parti socialiste français", -5), ("les républicains", 4),
    ("christlich demokratische", 3), ("union démocrate", 3), ("sozialdemokratische partei", -3), ("alternative für deutschland", 8),
    ("die grünen", -1), ("die linke", -6), ("freie demokratische", 1),
    ("conservative party", 4), ("labour party", -4), ("reform uk", 7), ("liberal democrat", 1),
    ("fratelli d'italia", 7), (" lega ", 6), ("partito democratico", -3), ("forza italia", 4),
    ("partido popular", 4), ("psoe", -4), (" vox ", 8), ("sumar", -6),
    ("prawo i sprawiedliwość", 6), ("koalicja obywatelska", 1),
    ("fidesz", 7),
    ("chega", 7), ("partido social democrata", 3),  # Portugal PSD — malgré le nom, centre-droit libéral
    ("vvd", 3), ("pvv", 8), ("d66", 0),
    ("moderaterna", 4), ("sverigedemokraterna", 7), ("socialdemokraterna", -4),
    ("arbeiderpartiet", -4), ("høyre", 4),
    ("socialdemokratiet", -3), ("venstre", 3),
    ("kokoomus", 3),
    ("fianna fáil", 1), ("fine gael", 2), ("sinn féin", -4),
    ("nea dimokratia", 4), ("syriza", -6),
    ("adalet ve kalkınma", 5), (" akp ", 5), ("chp", -3),
    ("edinaïa rossia", 8), ("united russia", 8),
    (" ods ", 3), (" ano ", 0),
    ("övp", 3), ("fpö", 8), ("spö", -3),
    ("union démocratique du centre", 6), ("udc suisse", 6), ("parti socialiste suisse", -3),

    # — AMÉRIQUES —
    ("republican party", 5), ("democratic party", -3),
    ("morena", -4), (" pan ", 4), (" pri ", 0),  # Mexique
    ("la libertad avanza", 8), ("propuesta republicana", 4),  # Argentine PRO
    ("frente amplio", -5),  # Chili et Uruguay — les deux nettement à gauche
    ("chile vamos", 3),
    ("fuerza popular", 5), ("perú libre", -6),
    ("psuv", -7), ("partido socialista unido de venezuela", -7),
    ("movimiento al socialismo", -6),
    ("partido colorado", 3),
    ("nuevas ideas", 5),  # Salvador, Bukele — populisme sécuritaire droite

    # — AFRIQUE —
    ("all progressives congress", 2),
    ("mostaqbal watan", 5),
    ("prosperity party", 2),  # Éthiopie, Abiy Ahmed
    ("union démocratique des bâtisseurs", 4), (" udb ", 4),  # Gabon, Oligui Nguema
    ("new patriotic party", 3), ("national democratic congress", -3),
    ("pastef", -4),
    ("chama cha mapinduzi", 3),
    ("national resistance movement", 5),
    ("rwandan patriotic front", 5),
    ("zanu-pf", 6),
    ("united party for national development", 1),
    ("swapo", -3),
    ("mpla", -1),
    ("frelimo", -2),
    ("rassemblement national démocratique", 4),  # Algérie RND
    ("pacto histórico", -6), ("historic pact", -6),  # Colombie, Petro — parti actuel (depuis 2025)
    ("colombia humana", -6), ("humane colombia", -6),  # Colombie, Petro — ancien parti (dissous mars 2026)
    ("african national congress", -3), (" anc ", -3),  # Afrique du Sud
    ("congolais du travail", 7),  # Congo-Brazzaville — régime personnaliste autoritaire
    ("botswana democratic party", 3), (" bdp ", 3),  # Botswana
    ("mouvement patriotique du salut", 5), ("patriotic salvation movement", 5),  # Tchad

    # — ASIE —
    ("communist party of china", -8), ("parti communiste chinois", -8),
    ("bharatiya janata party", 6), ("indian national congress", -2),
    ("jiyu-minshuto", 3),
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
    ("liberal party of australia", 4), (" alp ", -3), ("nationals", 5),
    ("national party nouvelle-zélande", 3),

    # — DÉJÀ VÉRIFIÉES INDIVIDUELLEMENT (recherche web) —
    ("partido dos trabalhadores", -6), ("workers' party", -6),  # Brésil, Lula

    # ══ MOTS-CLÉS GÉNÉRIQUES — filet de secours uniquement ══
    # Utilisés seulement si aucune correspondance précise ci-dessus n'a
    # été trouvée. Attention : un mot-clé générique peut matcher à tort
    # un nom de parti qui le contient par coïncidence sans que ça reflète
    # sa vraie orientation (voir cas du PSD portugais, corrigé ci-dessus
    # en le plaçant en priorité).
    ("extrême droite", 8), ("far-right", 8), ("far right", 8),
    ("extrême gauche", -8), ("far-left", -8), ("far left", -8),
    ("nationalisme", 6), ("nationalist", 6), ("nationalism", 6),
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
    ou à défaut du nom du parti. Retourne None (pas 0) si aucune donnée
    n'est disponible — un régime militaire/de transition sans parti n'est
    pas "centriste", c'est juste une donnée manquante. Confondre les deux
    afficherait à tort un dirigeant autoritaire comme modéré."""
    def normaliser(s):
        # Wikidata utilise souvent l'apostrophe typographique (') plutôt
        # que l'apostrophe droite ('), ce qui cassait silencieusement des
        # correspondances comme "Workers' Party" — normalisation nécessaire
        # avant toute comparaison, sinon un mot-clé pourtant correct ne
        # matche jamais.
        return s.lower().replace("\u2019", "'").replace("\u2018", "'")
    textes = [normaliser(t) for t in libelles_ideologie if t] + [normaliser(nom_parti or "")]
    for texte in textes:
        for mot, score in MOTS_CLES_POSITION:
            if normaliser(mot) in texte:
                return score
    # Aucun mot-clé trouvé : si le parti est vide ou générique (indépendant,
    # sans étiquette, transition militaire...), on ne sait vraiment rien —
    # ne pas prétendre "centre" par défaut.
    return None

# ══════════════════════════════════════
# REQUÊTE WIKIDATA — chef d'État (P35) et chef de gouvernement (P6),
# avec code ISO du pays (P297) et rang de la déclaration.
# ══════════════════════════════════════
QUERY_DIRIGEANTS = """
SELECT ?pays ?paysLabel ?iso
       ?hos ?hosLabel ?hosRank ?hosPartyItemLabel ?hosStart ?hosIdeoItemLabel
       ?hog ?hogLabel ?hogRank ?hogPartyItemLabel ?hogStart ?hogIdeoItemLabel
WHERE {
  ?pays wdt:P31 wd:Q3624078.
  OPTIONAL { ?pays wdt:P297 ?iso. }
  OPTIONAL {
    ?pays p:P35 ?hosStmt.
    ?hosStmt ps:P35 ?hos; wikibase:rank ?hosRank.
    FILTER(?hosRank != wikibase:DeprecatedRank)
    FILTER NOT EXISTS { ?hosStmt pq:P582 ?hosEnd. }
    OPTIONAL { ?hosStmt pq:P580 ?hosStart. }
    OPTIONAL { ?hos wdt:P102 ?hosPartyItem.
      OPTIONAL { ?hosPartyItem wdt:P1387 ?hosIdeoItem. } }
  }
  OPTIONAL {
    ?pays p:P6 ?hogStmt.
    ?hogStmt ps:P6 ?hog; wikibase:rank ?hogRank.
    FILTER(?hogRank != wikibase:DeprecatedRank)
    FILTER NOT EXISTS { ?hogStmt pq:P582 ?hogEnd. }
    OPTIONAL { ?hogStmt pq:P580 ?hogStart. }
    OPTIONAL { ?hog wdt:P102 ?hogPartyItem.
      OPTIONAL { ?hogPartyItem wdt:P1387 ?hogIdeoItem. } }
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
"""

def wikidata_query(query):
    try:
        r = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/json", "User-Agent": "Geolandar-Dirigeants/2.0 (geolandar.fr)"},
            timeout=120
        )
        r.raise_for_status()
        return r.json()["results"]["bindings"]
    except Exception as e:
        print(f"  Erreur requête Wikidata: {type(e).__name__} — {e}")
        return []

def fmt_date(valeur_iso):
    if not valeur_iso:
        return None
    try:
        return datetime.fromisoformat(valeur_iso.replace("Z", "")).strftime("%d/%m/%Y")
    except Exception:
        return None

def v(ligne, cle):
    return ligne.get(cle, {}).get("value", "")

def construire_dirigeants(lignes):
    """Regroupe les lignes Wikidata par pays (nom du site) et choisit le bon titulaire."""
    par_pays = {}
    hors_site = set()
    for ligne in lignes:
        qid = v(ligne, "pays").split("/")[-1]
        pays = pays_site(v(ligne, "paysLabel"), v(ligne, "iso"), qid)
        if not pays:
            if v(ligne, "paysLabel"):
                hors_site.add(v(ligne, "paysLabel"))
            continue
        entree = par_pays.setdefault(pays, {"hos": {}, "hog": {}})
        for role in ("hos", "hog"):
            nom = v(ligne, role + "Label")
            if not nom or not v(ligne, role) or QID_BRUT.match(nom.strip()):
                continue
            info = entree[role].setdefault(nom, {"parti": "", "start": "", "ideologie": "", "prefere": False})
            info["parti"] = info["parti"] or v(ligne, role + "PartyItemLabel")
            info["ideologie"] = info["ideologie"] or v(ligne, role + "IdeoItemLabel")
            debut = v(ligne, role + "Start")
            if debut > info["start"]:
                info["start"] = debut
            if v(ligne, role + "Rank").endswith("PreferredRank"):
                info["prefere"] = True

    if hors_site:
        print(f"  ℹ {len(hors_site)} États Wikidata absents du site (ignorés) : {', '.join(sorted(hors_site))}")

    resultats = {}
    aujourd_hui = date.today().isoformat()
    for pays, entree in par_pays.items():
        if pays in PAYS_IGNORES:
            continue
        role = "hos" if pays in PAYS_HOS else "hog"
        candidats = {n: i for n, i in entree[role].items() if (i["start"] or "")[:10] <= aujourd_hui}
        if not candidats:
            continue
        ambigu = len(candidats) > 1
        # Choix : déclaration « préférée » d'abord, puis la prise de fonction la plus récente.
        nom = sorted(candidats, key=lambda n: (candidats[n]["prefere"], candidats[n]["start"]), reverse=True)[0]
        info = candidats[nom]
        # Ambiguïté levée si une seule déclaration est « préférée »
        if ambigu and sum(1 for i in candidats.values() if i["prefere"]) == 1:
            ambigu = False
        parti, ideologie = info["parti"], info["ideologie"]
        date_debut = fmt_date(info["start"])
        titre = "Chef d'État" if role == "hos" else "Chef du gouvernement"
        position = deduire_position([ideologie] if ideologie else [], parti)
        fiabilite = 4 if ambigu else (3 if not date_debut else 1)
        description = (f"{nom}, {titre.lower()} depuis le {date_debut}." if date_debut
                       else f"{nom}, {titre.lower()} (date de prise de fonction non renseignée sur Wikidata).")
        if parti:
            description += f" Parti : {parti}."
        if ambigu:
            description += " ⚠️ Plusieurs titulaires actuels détectés sur Wikidata — à vérifier."
        resultats[pays] = {"pays": pays, "nom": nom, "titre": titre, "parti": parti, "position": position,
                           "description": description, "fiabilite": fiabilite,
                           "autres": sorted(n for n in candidats if n != nom)}
    return resultats

def appliquer_corrections(dirigeants):
    """Remplace un titulaire périmé renvoyé par Wikidata, uniquement si Wikidata
    renvoie encore l'ancien nom."""
    for pays, c in CORRECTIONS.items():
        d = dirigeants.get(pays)
        if not d:
            continue
        noms_wd = [d["nom"]] + d.get("autres", [])
        if d["nom"] == c["nom"]:
            print(f"  ✓ {pays} : Wikidata est à jour ({c['nom']}) — la correction manuelle peut être retirée")
            continue
        if not any(n in c["si_wikidata"] for n in noms_wd) and c["nom"] not in noms_wd:
            print(f"  ⚠ {pays} : Wikidata renvoie « {d['nom']} », ni l'ancien ni le titulaire attendu — correction NON appliquée, à vérifier")
            continue
        print(f"  ✎ {pays} : Wikidata renvoie « {d['nom']} » (périmé) → {c['nom']}")
        d.update({"nom": c["nom"], "titre": c["titre"], "parti": "", "position": None, "fiabilite": 1,
                  "description": f"{c['nom']}, {c['titre'].lower()} depuis {c['depuis']}."})
    return dirigeants

def sauvegarder(dirigeants):
    total = 0
    for pays, d in dirigeants.items():
        try:
            supabase.table("dirigeants").upsert({
                "pays": d["pays"], "nom": d["nom"], "titre": d["titre"], "parti": d["parti"],
                "position": d["position"], "description": d["description"], "fiabilite": d["fiabilite"],
                "updated_at": datetime.now().isoformat(),
            }, on_conflict="pays").execute()
            total += 1
        except Exception as e:
            print(f"  ✗ {pays}: {e}")
    return total

def main():
    print("=" * 60)
    print("  GEOLANDAR — Mise à jour automatique des dirigeants v2.0")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print("  Interrogation de Wikidata (chefs d'État et de gouvernement)...")
    lignes = wikidata_query(QUERY_DIRIGEANTS)
    print(f"  {len(lignes)} lignes reçues")
    if not lignes:
        print("  Aucune donnée reçue : rien n'est modifié dans Supabase.")
        return
    dirigeants = appliquer_corrections(construire_dirigeants(lignes))
    print(f"\n  {len(dirigeants)} pays avec un dirigeant identifié")
    if supabase is None:
        print("  (pas de clé Supabase : essai à blanc, rien n'est écrit)")
        for p in sorted(dirigeants):
            print(f"   {p}: {dirigeants[p]['nom']} [{dirigeants[p]['fiabilite']}]")
        return
    print("\n  Écriture dans Supabase...")
    total = sauvegarder(dirigeants)
    ambigus = [p for p, d in dirigeants.items() if d["fiabilite"] == 4]
    incertains = [p for p, d in dirigeants.items() if d["fiabilite"] == 3]
    if ambigus:
        print(f"\n  ⚠️  {len(ambigus)} pays avec plusieurs titulaires détectés (à vérifier) :")
        for p in sorted(ambigus):
            print(f"     - {p} : {dirigeants[p]['nom']} (autres : {', '.join(dirigeants[p]['autres'])})")
    if incertains:
        print(f"\n  🟠 {len(incertains)} pays sans date de prise de fonction connue : {', '.join(sorted(incertains))}")
    print(f"\n{'=' * 60}\n  TOTAL: {total} dirigeants mis à jour\n  Terminé: {datetime.now().strftime('%H:%M:%S')}\n{'=' * 60}")

if __name__ == "__main__":
    main()
