"""Catalogue des mesures « bonus » : chaque montre n'en fournit qu'une partie.
L'app n'affiche que celles qui existent vraiment dans tes données."""
from __future__ import annotations

from typing import Any, Optional

# ------------------------------------------------------------ mesures quotidiennes
# clé interne : (libellé, unité, décimales, agrégation sur 7 jours : "moy" ou "somme")
QUOTIDIEN = {
    "pas": ("Pas", "", 0, "moy"),
    "bb_max": ("Body Battery max", "", 0, "moy"),
    "bb_min": ("Body Battery min", "", 0, "moy"),
    "stress": ("Stress moyen", " /100", 0, "moy"),
    "fc_repos": ("FC au repos", " bpm", 0, "moy"),
    "spo2": ("SpO2 moyenne", " %", 0, "moy"),
    "respiration": ("Respiration", " /min", 1, "moy"),
    "intensite": ("Minutes intensives", " min", 0, "somme"),
    "etages": ("Étages montés", "", 0, "moy"),
    "calories_actives": ("Calories actives", " kcal", 0, "moy"),
    "recharge_ans": ("Recharge ANS", "", 1, "moy"),          # Polar
    "respiration_nuit": ("Respiration nocturne", " /min", 1, "moy"),  # Polar
}

# Clés possibles dans les résumés quotidiens Garmin (les noms varient selon les versions)
_GARMIN_QUOTIDIEN = {
    "pas": ("totalSteps", "steps"),
    "bb_max": ("bodyBatteryHighestValue", "bodyBatteryHigh", "maxBodyBattery"),
    "bb_min": ("bodyBatteryLowestValue", "bodyBatteryLow", "minBodyBattery"),
    "stress": ("averageStressLevel", "avgStressLevel", "overallStressLevel"),
    "fc_repos": ("restingHeartRate", "restingHeartRateValue"),
    "spo2": ("averageSpo2", "avgSpo2", "averageSpO2"),
    "respiration": ("avgWakingRespirationValue", "averageRespirationValue", "avgRespiration"),
    "etages": ("floorsAscended", "floorsClimbed"),
    "calories_actives": ("activeKilocalories", "activeCalories"),
}

# ------------------------------------------------------------ mesures par sortie
ACTIVITE = {
    "cadence": ("Cadence", " pas/min", 0),
    "cadence_velo": ("Cadence", " tr/min", 0),
    "puissance": ("Puissance moy.", " W", 0),
    "puissance_norm": ("Puissance normalisée", " W", 0),
    "te_aerobie": ("Effet aérobie", " /5", 1),
    "te_anaerobie": ("Effet anaérobie", " /5", 1),
    "charge": ("Charge (montre)", "", 0),
    "contact_sol": ("Contact au sol", " ms", 0),
    "oscillation": ("Oscillation verticale", " cm", 1),
    "foulee": ("Longueur de foulée", " m", 2),
    "denivele": ("Dénivelé +", " m", 0),
    "calories": ("Calories", " kcal", 0),
    "fc_max": ("FC max", " bpm", 0),
}

_GARMIN_ACTIVITE = {
    "cadence": ("averageRunningCadenceInStepsPerMinute", "avgRunCadence"),
    "cadence_velo": ("averageBikingCadenceInRevPerMinute", "avgBikeCadence"),
    "puissance": ("avgPower", "averagePower"),
    "puissance_norm": ("normPower", "normalizedPower"),
    "te_aerobie": ("aerobicTrainingEffect",),
    "te_anaerobie": ("anaerobicTrainingEffect",),
    "charge": ("activityTrainingLoad", "trainingLoad"),
    "contact_sol": ("avgGroundContactTime",),
    "oscillation": ("avgVerticalOscillation",),
    "foulee": ("avgStrideLength",),
    "calories": ("calories",),
}


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN


def _premier(d: dict, cles) -> Optional[float]:
    for c in cles:
        v = _num(d.get(c))
        if v is not None:
            return v
    return None


def garmin_quotidien(item: dict) -> dict:
    res = {k: _premier(item, cles) for k, cles in _GARMIN_QUOTIDIEN.items()}
    mod, vig = _num(item.get("moderateIntensityMinutes")), _num(item.get("vigorousIntensityMinutes"))
    if mod is not None or vig is not None:
        res["intensite"] = (mod or 0) + 2 * (vig or 0)   # même règle que Garmin : intense compte double
    return {k: v for k, v in res.items() if v is not None}


def garmin_activite(a: dict) -> dict:
    res = {k: _premier(a, cles) for k, cles in _GARMIN_ACTIVITE.items()}
    if res.get("foulee") and res["foulee"] > 10:     # Garmin la donne en cm
        res["foulee"] = res["foulee"] / 100
    if res.get("oscillation") and res["oscillation"] > 30:  # parfois en mm
        res["oscillation"] = res["oscillation"] / 10
    return {k: round(v, 2) for k, v in res.items() if v is not None and v > 0}


def formater(cle: str, valeur: Any, catalogue: dict = None) -> str:
    cat = catalogue or {**QUOTIDIEN, **{k: (*v, "moy") for k, v in ACTIVITE.items()}}
    lib, unite, dec = cat[cle][0], cat[cle][1], cat[cle][2]
    v = _num(valeur)
    if v is None:
        return "–"
    txt = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return f"{txt}{unite}"
