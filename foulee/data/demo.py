"""Données de démonstration : 6 mois d'une coureuse fictive, pour essayer
l'app sans clé Garmin. Tout est généré, rien n'est réel."""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from ..engine import vdot as V
from ..engine.seances import EFFORT, Seance

FC_MAX, FC_REPOS = 188, 48


def _allure_e(vd):
    lo, hi = V.allures(vd)["E"]
    return (lo + hi) / 2


def historique(aujourd_hui: date, jours: int = 185, graine: int = 7):
    rng = random.Random(graine)
    nrng = np.random.default_rng(graine)
    debut = aujourd_hui - timedelta(days=jours)
    acts, vfc, som = [], [], []
    base_vfc = 61.0
    fatigue = 0.0
    for k in range(jours):
        j = debut + timedelta(days=k)
        vd = 41.5 + 2.5 * k / jours
        pause = date(j.year, 9, 8) <= j <= date(j.year, 9, 26)   # « petite blessure » en septembre
        wd = j.weekday()
        sortie = None
        if not pause and rng.random() > 0.08:
            A = V.allures(vd)
            if wd == 1:
                km = rng.choice([8, 9, 10])
                allure = (A["T"][0] + A["E"][0]) / 2
                sortie = ("Fractionné", km, allure, rng.randint(152, 162), rng.randint(174, 186))
            elif wd in (3, 5):
                km = rng.choice([6, 7, 8])
                sortie = ("Footing", km, _allure_e(vd) + rng.uniform(-8, 8), rng.randint(131, 140), rng.randint(152, 162))
            elif wd == 6:
                km = min(8 + k / jours * 10 + rng.uniform(-1, 1), 18)
                sortie = ("Sortie longue", round(km, 1), _allure_e(vd) + rng.uniform(0, 10), rng.randint(135, 144), rng.randint(158, 166))
        charge = 0.0
        if not pause and wd == 2 and k % 14 < 7:   # home trainer un mercredi sur deux
            acts.append({"id": f"demo-velo-{j.isoformat()}", "date": j, "debut": f"{j.isoformat()}T19:00:00",
                         "nom": "Home trainer", "distance_km": 30.0, "duree_s": 3600, "fc_moy": 128,
                         "fc_max": 150, "denivele": 0, "sport": "velo"})
        if sortie:
            nom, km, allure, fcm, fcx = sortie
            duree = km * allure
            h = 7 + rng.randint(0, 11)
            acts.append({"id": f"demo-{j.isoformat()}", "date": j, "debut": f"{j.isoformat()}T{h:02d}:{rng.randint(0, 59):02d}:00",
                         "nom": nom, "distance_km": round(km, 2), "duree_s": round(duree), "fc_moy": fcm,
                         "fc_max": fcx, "denivele": rng.randint(20, 160), "sport": "course"})
            charge = duree / 60 * (1.6 if nom == "Fractionné" else 1.0)
        fatigue = fatigue * 0.6 + charge / 25
        nuit = base_vfc + nrng.normal(0, 3.2) - fatigue * 1.6 + (k / jours) * 2
        vfc.append({"date": j, "nuit": round(nuit, 1), "moy_7j": None, "zone_basse": None,
                    "zone_haute": None, "statut": ""})
        heures = float(np.clip(nrng.normal(7.3, 0.55), 5.6, 8.9))
        som.append({"date": j, "heures": round(heures, 2), "score": int(np.clip(60 + (heures - 6) * 12 + nrng.normal(0, 4), 40, 97)),
                    "fc_repos": int(round(FC_REPOS + fatigue * 1.5 + nrng.normal(0, 1.2)))})
    return pd.DataFrame(acts), pd.DataFrame(vfc), pd.DataFrame(som)


def simuler_suivi(seances: list[Seance], jusqua: date, graine: int = 3) -> pd.DataFrame:
    """Sorties « faites » qui suivent le plan (une séance sautée de temps en temps)."""
    rng = random.Random(graine)
    lignes = []
    for s in seances:
        if s.sport not in ("course", "velo") or s.jour > jusqua or rng.random() < 0.1:
            continue
        if s.sport == "velo":
            lignes.append({"id": f"demo-velo-{s.jour.isoformat()}", "date": s.jour, "debut": f"{s.jour.isoformat()}T19:00:00",
                           "nom": "Home trainer", "distance_km": round(s.minutes / 60 * 29, 1), "duree_s": s.minutes * 60,
                           "fc_moy": 126 + rng.randint(-4, 6), "fc_max": 150, "denivele": 0, "sport": "velo"})
            continue
        duree = s.minutes * 60 * rng.uniform(0.97, 1.05)
        km = s.km * rng.uniform(0.97, 1.03)
        fcm = {"footing": 136, "long": 140}.get(s.genre, 158) + rng.randint(-3, 3)
        heure = "07:15:00" if s.jour == jusqua else "18:30:00"
        lignes.append({"id": f"demo-{s.jour.isoformat()}", "date": s.jour, "debut": f"{s.jour.isoformat()}T{heure}",
                       "nom": s.titre.split("·")[0].strip(), "distance_km": round(km, 2), "duree_s": round(duree),
                       "fc_moy": fcm, "fc_max": fcm + 18, "denivele": rng.randint(20, 120), "sport": "course"})
    return pd.DataFrame(lignes)


def tours_simules(seance: Seance, graine: str) -> list[dict]:
    """Tours (laps) plausibles qui suivent les étapes de la séance."""
    rng = random.Random(graine)
    tours = []
    for b in seance.blocs:
        for _ in range(b.repetitions):
            for e in b.etapes:
                cible = ((e.allure_min or 0) + (e.allure_max or 0)) / 2 or 360
                ecart = rng.choice([-0.01, 0.0, 0.005, 0.012, 0.03]) if e.type == EFFORT else rng.uniform(-0.03, 0.05)
                allure = cible * (1 + ecart)
                if e.distance_m:
                    dist, duree = e.distance_m, e.distance_m / 1000 * allure
                else:
                    duree = e.duree_s or 60
                    dist = duree / allure * 1000
                tours.append({"duree_s": duree, "distance_m": dist, "fc_moy": 150, "allure": allure})
    return tours
