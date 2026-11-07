"""VFC nocturne : zone habituelle, tendance sur 7 jours et « météo intérieure ».

Principe de l'entraînement guidé par la VFC (Kiviniemi 2007, Plews 2013) :
on compare la moyenne glissante sur 7 nuits à la zone habituelle de la
personne. Si Garmin fournit déjà sa zone (« baseline »), on l'utilise."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd

SOLEIL, ECLAIRCIES, NUAGES, ORAGE, VOILE, INCONNU = "soleil", "eclaircies", "nuages", "orage", "voile", "inconnu"

TEXTES = {
    SOLEIL: ("Grand soleil", "Feu vert pour la séance prévue."),
    ECLAIRCIES: ("Éclaircies", "Petite nuit en dessous de ta zone, mais la tendance tient. On garde le plan, à l'écoute."),
    NUAGES: ("Ciel nuageux", "Ta VFC est sous ta zone depuis quelques jours. Aujourd'hui, on lève le pied."),
    ORAGE: ("Orage", "Plusieurs nuits très basses : repos ou balade. Ton corps récupère."),
    VOILE: ("Ciel voilé", "VFC au-dessus de ta zone : parfois signe de fatigue ou de début de rhume. Prudence."),
    INCONNU: ("Météo en attente", "Pas encore assez de nuits enregistrées pour connaître ta zone."),
}


@dataclass
class Meteo:
    etat: str
    titre: str
    texte: str
    derniere_nuit: Optional[float]
    moyenne_7j: Optional[float]
    zone_basse: Optional[float]
    zone_haute: Optional[float]

    @property
    def lever_le_pied(self) -> bool:
        return self.etat in (NUAGES, ORAGE)


def zone_habituelle(vfc: pd.DataFrame, jour: date) -> tuple[Optional[float], Optional[float]]:
    if vfc is None or vfc.empty:
        return None, None
    ligne = vfc[vfc["date"] <= jour].tail(1)
    if not ligne.empty:
        lo, hi = ligne.iloc[0].get("zone_basse"), ligne.iloc[0].get("zone_haute")
        if pd.notna(lo) and pd.notna(hi) and lo and hi:
            return float(lo), float(hi)
    # Zone calculée : 60 nuits, hors 7 dernières, moyenne ± 1 écart-type
    debut, fin = jour - timedelta(days=67), jour - timedelta(days=7)
    hist = vfc[(vfc["date"] > debut) & (vfc["date"] <= fin)]["nuit"].dropna()
    if len(hist) < 14:
        return None, None
    m, s = hist.mean(), max(hist.std(), 2.0)
    return round(m - s, 1), round(m + s, 1)


def meteo(vfc: pd.DataFrame, jour: date) -> Meteo:
    lo, hi = zone_habituelle(vfc, jour)
    if vfc is None or vfc.empty or lo is None:
        t, x = TEXTES[INCONNU]
        return Meteo(INCONNU, t, x, None, None, lo, hi)
    recentes = vfc[(vfc["date"] > jour - timedelta(days=7)) & (vfc["date"] <= jour)]["nuit"].dropna()
    derniere = vfc[vfc["date"] <= jour]["nuit"].dropna()
    derniere = float(derniere.iloc[-1]) if not derniere.empty else None
    moy7 = float(recentes.mean()) if len(recentes) >= 3 else derniere
    trois = vfc[(vfc["date"] > jour - timedelta(days=3)) & (vfc["date"] <= jour)]["nuit"].dropna()
    if moy7 is None:
        etat = INCONNU
    elif moy7 > hi:
        etat = VOILE
    elif moy7 < lo:
        etat = ORAGE if len(trois) >= 2 and (trois < lo - (hi - lo) * 0.25).sum() >= 2 else NUAGES
    elif derniere is not None and derniere < lo:
        etat = ECLAIRCIES
    else:
        etat = SOLEIL
    t, x = TEXTES[etat]
    return Meteo(etat, t, x, derniere, moy7, lo, hi)
