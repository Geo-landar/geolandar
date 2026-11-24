# GEOLANDAR — Ce que l'automatisation n'a pas pu mettre à jour seule.
# Chaque script note ses cas dans rapport/<section>.json ; rapport_manuel.py
# les rassemble chaque nuit dans data/a_mettre_a_jour.json (lu par le
# récapitulatif mensuel) et ouvre un ticket GitHub (→ e-mail) pour les urgences.
import json, os
DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapport")

def noter(section, elements):
    try:
        os.makedirs(DOSSIER, exist_ok=True)
        json.dump(list(elements), open(os.path.join(DOSSIER, section + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"  (rapport {section} non écrit : {e})")
