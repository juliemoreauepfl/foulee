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
                         "fc_max": fcx, "denivele": rng.randint(20, 160), "sport": "course",
                         "extras": _extras_course(rng, nom)})
            charge = duree / 60 * (1.6 if nom == "Fractionné" else 1.0)
        fatigue = fatigue * 0.6 + charge / 25
        nuit = base_vfc + nrng.normal(0, 3.2) - fatigue * 1.6 + (k / jours) * 2
        vfc.append({"date": j, "nuit": round(nuit, 1), "moy_7j": None, "zone_basse": None,
                    "zone_haute": None, "statut": ""})
        heures = float(np.clip(nrng.normal(7.3, 0.55), 5.6, 8.9))
        som.append({"date": j, "heures": round(heures, 2), "score": int(np.clip(60 + (heures - 6) * 12 + nrng.normal(0, 4), 40, 97)),
                    "fc_repos": int(round(FC_REPOS + fatigue * 1.5 + nrng.normal(0, 1.2)))})
    return pd.DataFrame(acts), pd.DataFrame(vfc), pd.DataFrame(som)


def _extras_course(rng, genre) -> dict:
    """Mesures avancées d'une montre type Forerunner (pas de capteur de puissance ici)."""
    dur = genre in ("Fractionné", "vma", "seuil", "cotes", "fartlek", "specifique")
    return {"cadence": rng.randint(168, 176) + (6 if dur else 0),
            "te_aerobie": round(rng.uniform(3.4, 4.2) if dur else rng.uniform(2.4, 3.2), 1),
            "te_anaerobie": round(rng.uniform(1.8, 3.1) if dur else rng.uniform(0.0, 0.6), 1),
            "charge": rng.randint(110, 190) if dur else rng.randint(50, 110),
            "calories": rng.randint(350, 750)}


def quotidien(aujourd_hui: date, jours: int = 60, graine: int = 11) -> pd.DataFrame:
    rng = random.Random(graine)
    lignes = []
    for k in range(jours):
        j = aujourd_hui - timedelta(days=jours - 1 - k)
        bb_max = rng.randint(62, 96)
        lignes.append({"date": j, "pas": rng.randint(6500, 14500), "bb_max": bb_max,
                       "bb_min": max(5, bb_max - rng.randint(45, 75)), "stress": rng.randint(22, 41),
                       "fc_repos": rng.randint(46, 52), "intensite": rng.randint(10, 75),
                       "etages": rng.randint(3, 18), "calories_actives": rng.randint(350, 1100),
                       "respiration": round(rng.uniform(13.0, 15.5), 1)})
    return pd.DataFrame(lignes)


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
                       "fc_moy": fcm, "fc_max": fcm + 18, "denivele": rng.randint(20, 120), "sport": "course",
                       "extras": _extras_course(rng, s.genre)})
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


def flux_simule(seance, act: dict, fc_repos: float = 52, fc_max: float = 190) -> list[dict]:
    """Courbe de FC plausible qui suit les étapes de la séance (mode démo)."""
    from ..engine.seances import ECHAUFFEMENT, RECUP, RETOUR
    rng = random.Random(str(act.get("id")))
    r = fc_max - fc_repos
    etapes = []
    if seance is not None and seance.blocs:
        for b in seance.blocs:
            for _ in range(b.repetitions):
                for e in b.etapes:
                    allure = ((e.allure_min or 0) + (e.allure_max or 0)) / 2 or 360
                    duree = e.duree_s or (e.distance_m / 1000 * allure if e.distance_m else 60)
                    cible = {ECHAUFFEMENT: 0.62, RETOUR: 0.6, RECUP: 0.66}.get(e.type, 0.86 if e.type == EFFORT else 0.66)
                    etapes.append((duree, cible, 1000 / allure))
    else:
        etapes.append((act.get("duree_s", 2400), 0.66, act["distance_km"] * 1000 / max(act.get("duree_s", 1), 1)))
    total = sum(d for d, _, _ in etapes) or 1
    echelle = act.get("duree_s", total) / total
    flux, t, fc, d = [], 0, fc_repos + 0.3 * r, 0.0
    derive = rng.uniform(0.0, 0.07)
    for duree, cible, v in etapes:
        fin = t + duree * echelle
        while t < fin:
            but = fc_repos + cible * r * (1 + derive * t / max(act.get("duree_s", 1), 1))
            fc += (but - fc) * 0.12 + rng.uniform(-1.2, 1.2)
            d += v * 5
            flux.append({"t": int(t), "fc": round(fc), "v": round(v * rng.uniform(0.97, 1.03), 2), "d": round(d)})
            t += 5
    return flux
