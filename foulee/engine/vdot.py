"""Niveau (VDOT) et allures d'entraînement, d'après les équations publiques
de Daniels & Gilbert (Oxygen Power, 1979) utilisées dans « Daniels' Running Formula »."""
from __future__ import annotations

import math
from typing import Optional

DISTANCES = {"5k": 5000.0, "10k": 10000.0, "semi": 21097.5, "marathon": 42195.0}
NOMS_DISTANCES = {"5k": "5 km", "10k": "10 km", "semi": "Semi-marathon", "marathon": "Marathon"}


def vo2_vitesse(v_m_min: float) -> float:
    """Coût en oxygène (ml/kg/min) à une vitesse donnée (m/min)."""
    return -4.60 + 0.182258 * v_m_min + 0.000104 * v_m_min ** 2


def fraction_vo2max(t_min: float) -> float:
    """Fraction de VO2max soutenable pendant t minutes."""
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t_min) + 0.2989558 * math.exp(-0.1932605 * t_min)


def vdot_depuis_course(distance_m: float, duree_s: float) -> Optional[float]:
    if not distance_m or not duree_s or duree_s < 180:
        return None
    t = duree_s / 60
    v = distance_m / t
    return vo2_vitesse(v) / fraction_vo2max(t)


def vitesse_pour_vo2(vo2: float) -> float:
    """Inverse de vo2_vitesse : m/min pour un coût donné."""
    a, b, c = 0.000104, 0.182258, -4.60 - vo2
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def allure_fraction(vdot: float, fraction: float) -> float:
    """Allure (s/km) correspondant à une fraction de VDOT."""
    v = vitesse_pour_vo2(vdot * fraction)
    return 60000.0 / v


def temps_predit(vdot: float, distance_m: float) -> float:
    """Temps de course prédit (s) pour un VDOT, par dichotomie."""
    lo, hi = 60.0, 60 * 60 * 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if vdot_depuis_course(distance_m, mid) > vdot:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def allures(vdot: float) -> dict[str, tuple[int, int]]:
    """Fourchettes d'allure en s/km : (rapide, lente)."""
    m = temps_predit(vdot, 42195) / 42.195
    t = allure_fraction(vdot, 0.88)
    i = allure_fraction(vdot, 0.975)
    r = allure_fraction(vdot, 1.05)
    return {
        "E": (round(allure_fraction(vdot, 0.70)), round(allure_fraction(vdot, 0.62))),
        "M": (round(m - 4), round(m + 4)),
        "T": (round(t - 4), round(t + 4)),
        "I": (round(i - 4), round(i + 4)),
        "R": (round(r - 3), round(r + 3)),
    }


def allure_course(vdot: float, code_distance: str) -> float:
    d = DISTANCES[code_distance]
    return temps_predit(vdot, d) / (d / 1000)


def vo2max_par_cardio(distance_m: float, duree_s: float, fc_moy: float, fc_repos: float, fc_max: float) -> Optional[float]:
    """VO2max estimée d'une sortie régulière via la relation %FC de réserve ≈ %VO2 de réserve
    (Swain & Leutholtz, 1997) : VO2max = (VO2 à cette vitesse − 3,5) / %FCR + 3,5."""
    if not (distance_m and duree_s and fc_moy and fc_max) or fc_max <= fc_repos + 30:
        return None
    hrr = (fc_moy - fc_repos) / (fc_max - fc_repos)
    if not 0.6 <= hrr <= 0.92:   # trop facile ou trop haché : estimation peu fiable
        return None
    return (vo2_vitesse(distance_m / (duree_s / 60)) - 3.5) / hrr + 3.5


def vdot_depuis_historique(activites, aujourd_hui=None, semaines: int = 12,
                           fc_repos: Optional[float] = None, fc_max: Optional[float] = None) -> Optional[float]:
    """Estimation du niveau à partir des sorties récentes.

    1. Par la performance : VDOT de chaque sortie de plus de 3 km, haut du
       panier (90e centile des 8 meilleures). Les footings le sous-estiment.
    2. Par le cardio, si la FC est disponible : médiane de la moitié haute
       des estimations « allure + FC ». Fiable même sans jamais courir à fond.
    On garde la plus haute des deux (bornée pour éviter les GPS farceurs).
    """
    import pandas as pd

    if activites is None or len(activites) == 0:
        return None
    df = activites.copy()
    if aujourd_hui is not None:
        debut = pd.Timestamp(aujourd_hui) - pd.Timedelta(weeks=semaines)
        recent = df[df["date"] >= debut.date()]
        if len(recent) >= 4:
            df = recent
    df = df[(df["distance_km"] >= 3) & (df["duree_s"] > 0)]
    if df.empty:
        return None
    valeurs = sorted(
        (v for v in (vdot_depuis_course(r.distance_km * 1000, r.duree_s) for r in df.itertuples()) if v),
        reverse=True,
    )[:8]
    if not valeurs:
        return None
    valeurs.sort()
    idx = max(0, int(round(0.9 * (len(valeurs) - 1))))
    perf = valeurs[idx]

    cardio = None
    if "fc_moy" in df and df["fc_moy"].notna().sum() >= 5:
        fcm = fc_max
        if fcm is None and "fc_max" in df:
            v = pd.to_numeric(df["fc_max"], errors="coerce").dropna()
            fcm = float(v.quantile(0.97)) if len(v) else None
        if fcm:
            est = sorted(x for x in (vo2max_par_cardio(r.distance_km * 1000, r.duree_s, r.fc_moy, fc_repos or 55.0, fcm)
                                     for r in df.itertuples() if pd.notna(r.fc_moy)) if x)
            if len(est) >= 5:
                haut = est[len(est) // 2:]
                cardio = haut[len(haut) // 2]
    meilleur = max(perf, min(cardio, perf * 1.25)) if cardio else perf
    return round(min(max(meilleur, 25.0), 85.0), 1)


def faisabilite(vdot_actuel: float, code_distance: str, objectif_s: Optional[int], semaines: int) -> tuple[str, float]:
    """Retourne (verdict, vdot_objectif)."""
    if not objectif_s:
        return ("Pas de chrono visé : on vise ta meilleure forme le jour J.", vdot_actuel)
    vdot_obj = vdot_depuis_course(DISTANCES[code_distance], objectif_s) or vdot_actuel
    ecart = vdot_obj - vdot_actuel
    # Ordre de grandeur : ~1 point de VDOT gagnable toutes les 3-4 semaines bien construites
    possible = max(semaines, 1) / 3.5
    pred = temps_predit(vdot_actuel, DISTANCES[code_distance])
    from .seances import fmt_duree
    if ecart <= 0:
        return (f"Dans tes cordes : aujourd'hui je te prédis {fmt_duree(pred)}.", vdot_obj)
    if ecart <= possible * 0.6:
        return (f"Réaliste en {semaines} semaines (aujourd'hui : {fmt_duree(pred)}).", vdot_obj)
    if ecart <= possible:
        return (f"Ambitieux mais faisable en {semaines} semaines (aujourd'hui : {fmt_duree(pred)}).", vdot_obj)
    return (f"Très ambitieux : aujourd'hui je te prédis {fmt_duree(pred)}. "
            "On peut viser plus doux et accélérer si tout roule.", vdot_obj)
