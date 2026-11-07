"""Données de la personne : chargement depuis Garmin (avec cache) ou démo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Optional

import pandas as pd

from . import demo
from .garmin import ClientGarmin

HISTORIQUE_JOURS = 183
COLS_ACT = ["id", "date", "debut", "nom", "distance_km", "duree_s", "fc_moy", "fc_max", "denivele", "sport", "extras"]
COLS_VFC = ["date", "nuit", "moy_7j", "zone_basse", "zone_haute", "statut"]
COLS_SOM = ["date", "heures", "score", "fc_repos"]


@dataclass
class Donnees:
    activites: pd.DataFrame
    vfc: pd.DataFrame
    sommeil: pd.DataFrame
    source: str  # "garmin" | "demo"
    maj: Optional[str] = None
    quotidien: Optional[pd.DataFrame] = None   # mesures bonus, selon la montre

    def fc_repos(self) -> float:
        """FC au repos : sommeil, sinon résumé du jour, sinon 55 par défaut."""
        for df in (self.sommeil, self.quotidien):
            if df is not None and not df.empty and "fc_repos" in df:
                v = pd.to_numeric(df["fc_repos"], errors="coerce").dropna().tail(14)
                if len(v):
                    return float(v.median())
        return 55.0


def _df(records, cols) -> pd.DataFrame:
    df = pd.DataFrame(records or [], columns=cols)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    if "sport" in cols:
        df["sport"] = df["sport"].fillna("course") if not df.empty else df["sport"]
    return df


def _vers_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    d = df.copy()
    d["date"] = d["date"].astype(str)
    return d.astype(object).where(d.notna(), None).to_dict("records")


def _df_libre(records) -> pd.DataFrame:
    df = pd.DataFrame(records or [])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def depuis_cache(cache: dict) -> Donnees:
    return Donnees(_df(cache.get("activites"), COLS_ACT), _df(cache.get("vfc"), COLS_VFC),
                   _df(cache.get("sommeil"), COLS_SOM), "garmin", cache.get("maj"),
                   _df_libre(cache.get("quotidien")))


def rafraichir(client: ClientGarmin, cache: Optional[dict], aujourd_hui: date,
               etape: Optional[Callable[[str, float], None]] = None) -> dict:
    """Met à jour le cache : historique complet la 1re fois, puis seulement les nouveautés."""
    cache = dict(cache or {})
    etape = etape or (lambda *_: None)
    debut_hist = aujourd_hui - timedelta(days=HISTORIQUE_JOURS)
    anciens = depuis_cache(cache)

    def depuis(df):
        if df is None or df.empty or "date" not in df:
            return debut_hist
        return max(debut_hist, max(df["date"]) - timedelta(days=3))

    limite = aujourd_hui - timedelta(days=400)

    def fusion(ancien: pd.DataFrame, nouveau: pd.DataFrame, cle: str) -> pd.DataFrame:
        """On ajoute sans jamais jeter l'ancien (Polar ne garde que 30 jours)."""
        if nouveau is None or nouveau.empty:
            return ancien
        if ancien is None or ancien.empty or "date" not in ancien:
            res = nouveau
        else:
            res = pd.concat([ancien, nouveau], ignore_index=True).drop_duplicates(cle, keep="last")
        return res[res["date"] >= limite].sort_values("date").reset_index(drop=True)

    etape("Sorties", 0.0)
    acts = fusion(anciens.activites, client.activites(depuis(anciens.activites), aujourd_hui), "id")
    etape("Sorties", 1.0)

    etape("VFC nocturne", 0.0)
    vfc = fusion(anciens.vfc, client.vfc(depuis(anciens.vfc), aujourd_hui), "date")
    etape("VFC nocturne", 1.0)

    etape("Sommeil", 0.0)
    d = depuis(anciens.sommeil)
    jours = [d + timedelta(days=k) for k in range((aujourd_hui - d).days + 1)]
    som = fusion(anciens.sommeil, client.sommeil(jours, lambda p: etape("Sommeil", p)), "date")
    etape("Sommeil", 1.0)

    # Mesures bonus : jamais bloquant (toutes les montres ne les ont pas)
    quot = anciens.quotidien
    try:
        if hasattr(client, "quotidien"):
            quot = fusion(anciens.quotidien, client.quotidien(depuis(anciens.quotidien), aujourd_hui), "date")
    except Exception:
        pass

    from datetime import datetime
    return {"activites": _vers_records(acts), "vfc": _vers_records(vfc), "sommeil": _vers_records(som),
            "quotidien": _vers_records(quot),
            "maj": datetime.now().isoformat(timespec="minutes")}


def donnees_demo(aujourd_hui: date) -> Donnees:
    a, v, s = demo.historique(aujourd_hui)
    return Donnees(a, v, s, "demo", aujourd_hui.isoformat(), demo.quotidien(aujourd_hui))


def courses(df: pd.DataFrame) -> pd.DataFrame:
    """Seulement la course à pied (pour le niveau, le volume, la plus longue sortie)."""
    if df is None or df.empty or "sport" not in df:
        return df
    return df[df["sport"].fillna("course") == "course"]


def filtrer_mois(df: pd.DataFrame, mois_exclus: list[str]) -> pd.DataFrame:
    if df is None or df.empty or not mois_exclus:
        return df
    cle = df["date"].map(lambda d: f"{d.year}-{d.month:02d}")
    return df[~cle.isin(set(mois_exclus))]
