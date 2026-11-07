"""Charge d'entraînement : TRIMP (Banister) et modèle forme / fatigue."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional

import pandas as pd

# Coefficients publiés du TRIMP de Banister
COEFS = {"femme": (0.86, 1.67), "homme": (0.64, 1.92), "": (0.75, 1.80)}
TAU_FORME, TAU_FATIGUE = 42, 7


def fc_max_estimee(activites: pd.DataFrame) -> Optional[float]:
    if activites is None or activites.empty or "fc_max" not in activites:
        return None
    vals = activites["fc_max"].dropna()
    vals = vals[(vals > 120) & (vals < 225)]
    if vals.empty:
        return None
    return float(vals.quantile(0.97))


def trimp(duree_s: float, fc_moy: Optional[float], fc_repos: float, fc_max: Optional[float],
          sexe: str = "", rpe: Optional[int] = None) -> float:
    """TRIMP d'une séance. Sans cardio : repli sur la méthode RPE de Foster
    (durée × effort ressenti), ramenée à une échelle comparable."""
    minutes = (duree_s or 0) / 60
    if fc_moy and fc_max and fc_max > fc_repos + 20:
        hrr = min(max((fc_moy - fc_repos) / (fc_max - fc_repos), 0), 1)
        k, b = COEFS.get(sexe, COEFS[""])
        return minutes * hrr * k * math.exp(b * hrr)
    effort = rpe if rpe else 4
    return minutes * effort * 0.22


def serie_charge(activites: pd.DataFrame, fc_repos: float, fc_max: Optional[float], sexe: str,
                 debut: date, fin: date) -> pd.DataFrame:
    """Charge quotidienne + forme (CTL), fatigue (ATL) et fraîcheur (TSB)."""
    jours = pd.date_range(debut, fin, freq="D").date
    charge = {j: 0.0 for j in jours}
    if activites is not None and not activites.empty:
        for r in activites.itertuples():
            if r.date in charge:
                charge[r.date] += trimp(r.duree_s, getattr(r, "fc_moy", None), fc_repos, fc_max, sexe)
    forme = fatigue = 0.0
    lignes = []
    for j in jours:
        c = charge[j]
        fraicheur = forme - fatigue  # calculée sur la veille
        forme += (c - forme) / TAU_FORME
        fatigue += (c - fatigue) / TAU_FATIGUE
        lignes.append({"date": j, "charge": c, "forme": forme, "fatigue": fatigue, "fraicheur": fraicheur})
    return pd.DataFrame(lignes)


def volume_hebdo(activites: pd.DataFrame, aujourd_hui: date, semaines: int = 4) -> float:
    if activites is None or activites.empty:
        return 0.0
    debut = aujourd_hui - timedelta(weeks=semaines)
    recent = activites[(activites["date"] >= debut) & (activites["date"] < aujourd_hui)]
    return float(recent["distance_km"].sum()) / semaines


def plus_longue(activites: pd.DataFrame, aujourd_hui: date, semaines: int = 10) -> float:
    if activites is None or activites.empty:
        return 0.0
    debut = aujourd_hui - timedelta(weeks=semaines)
    recent = activites[activites["date"] >= debut]
    return float(recent["distance_km"].max()) if not recent.empty else 0.0


def sorties_par_semaine(activites: pd.DataFrame, aujourd_hui: date, semaines: int = 8) -> float:
    if activites is None or activites.empty:
        return 0.0
    debut = aujourd_hui - timedelta(weeks=semaines)
    return len(activites[activites["date"] >= debut]) / semaines
