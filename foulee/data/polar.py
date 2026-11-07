"""Client Polar AccessLink v3 (gratuit, OAuth2).

Chacun crée son propre « client API » sur https://admin.polaraccesslink.com,
comme pour la clé Garmin : tes données restent les tiennes.
Limite importante : Polar ne garde que ~30 jours de sorties et ~28 nuits.
L'app accumule donc l'historique dans sa sauvegarde à chaque mise à jour."""
from __future__ import annotations

import re
import secrets as _secrets
from datetime import date, datetime, timedelta
from typing import Callable, Optional
from urllib.parse import urlencode

import pandas as pd
import requests

AUTH_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
API = "https://www.polaraccesslink.com"
SPORTS_COURSE = ("RUNNING", "TRAIL_RUNNING", "TREADMILL_RUNNING", "TRACK_AND_FIELD_RUNNING", "ROAD_RUNNING",
                 "ULTRARUNNING_RUNNING", "OTHER_RUNNING")


class PolarErreur(Exception):
    pass


# ------------------------------------------------------------ connexion OAuth2
def url_autorisation(client_id: str, redirect_uri: str, etat: Optional[str] = None) -> tuple[str, str]:
    etat = etat or _secrets.token_urlsafe(16)
    q = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
         "scope": "accesslink.read_all", "state": etat}
    return f"{AUTH_URL}?{urlencode(q)}", etat


def echanger_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    r = requests.post(TOKEN_URL, auth=(client_id, client_secret), timeout=30,
                      headers={"Accept": "application/json"},
                      data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})
    if not r.ok:
        raise PolarErreur(f"Polar refuse la connexion (code {r.status_code}). Le lien de retour (redirect URL) "
                          "déclaré sur admin.polaraccesslink.com doit être exactement l'adresse de ton app.")
    corps = r.json()
    jeton = {"access_token": corps["access_token"], "user_id": str(corps.get("x_user_id", "")),
             "obtenu": datetime.now().isoformat(timespec="seconds")}
    # Enregistrement (une seule fois ; 409 = déjà enregistré, c'est très bien)
    r2 = requests.post(f"{API}/v3/users", json={"member-id": f"foulee-{jeton['user_id']}"}, timeout=30,
                       headers={"Authorization": f"Bearer {jeton['access_token']}", "Accept": "application/json"})
    if r2.status_code == 403:
        raise PolarErreur("Polar demande d'accepter ses conditions : ouvre flow.polar.com, accepte-les, puis recommence.")
    if r2.status_code not in (200, 201, 204, 409):
        raise PolarErreur(f"Inscription Polar impossible (code {r2.status_code}).")
    return jeton


# ------------------------------------------------------------ client
class ClientPolar:
    """Mêmes méthodes que le client Garmin, pour que le reste de l'app ne voie pas la différence."""

    def __init__(self, jeton: dict, session: Optional[requests.Session] = None):
        if not jeton or not jeton.get("access_token"):
            raise PolarErreur("Compte Polar non connecté.")
        self.jeton = jeton
        self.http = session or requests.Session()

    def get(self, chemin: str, params: Optional[dict] = None, brut: bool = False):
        r = self.http.get(API + chemin, params=params, timeout=60,
                          headers={"Authorization": f"Bearer {self.jeton['access_token']}",
                                   "Accept": "*/*" if brut else "application/json"})
        if r.status_code in (401, 403):
            raise PolarErreur("Polar refuse l'accès : reconnecte ton compte dans les Réglages.")
        if r.status_code in (204, 404):
            return None
        if not r.ok:
            raise PolarErreur(f"Erreur Polar {r.status_code} sur {chemin}")
        if brut:
            return r.content
        return r.json() if r.content else None

    def verifier(self) -> bool:
        self.get("/v3/exercises")
        return True

    def activites(self, debut: date, fin: date) -> pd.DataFrame:
        rep = self.get("/v3/exercises") or []
        if isinstance(rep, dict):
            rep = rep.get("exercises") or []
        lignes = [x for x in (normaliser_exercice(e) for e in rep) if x and debut <= x["date"] <= fin]
        df = pd.DataFrame(lignes)
        if df.empty:
            return df
        return df[df["sport"] != "autre"].sort_values("debut").reset_index(drop=True)

    def fichier_activite(self, activite_id) -> Optional[bytes]:
        return self.get(f"/v3/exercises/{activite_id}/fit", brut=True)

    def vfc(self, debut: date, fin: date) -> pd.DataFrame:
        rep = self.get("/v3/users/nightly-recharge") or {}
        items = rep.get("recharges", []) if isinstance(rep, dict) else rep
        lignes = [x for x in (normaliser_recharge(i) for i in items) if x and debut <= x["date"] <= fin]
        return pd.DataFrame(lignes, columns=["date", "nuit", "moy_7j", "zone_basse", "zone_haute", "statut"])

    def quotidien(self, debut: date, fin: date) -> pd.DataFrame:
        rep = self.get("/v3/users/nightly-recharge") or {}
        lignes = []
        for i in (rep.get("recharges", []) if isinstance(rep, dict) else rep):
            jour = _date(i.get("date")) if isinstance(i, dict) else None
            if not jour or not (debut <= jour <= fin):
                continue
            m = {k: v for k, v in {"recharge_ans": i.get("ans_charge"),
                                   "respiration_nuit": i.get("breathing_rate_avg")}.items() if v is not None}
            if m:
                lignes.append({"date": jour, **m})
        return pd.DataFrame(lignes)

    def sommeil(self, jours: list[date], progression: Optional[Callable[[float], None]] = None) -> pd.DataFrame:
        rep = self.get("/v3/users/sleep") or {}
        items = rep.get("nights", []) if isinstance(rep, dict) else rep
        voulus = set(jours)
        lignes = [x for x in (normaliser_nuit(i) for i in items) if x and (not voulus or x["date"] in voulus)]
        # FC moyenne de la nuit, depuis Nightly Recharge
        rec = self.get("/v3/users/nightly-recharge") or {}
        fc = {}
        for i in (rec.get("recharges", []) if isinstance(rec, dict) else rec):
            n = normaliser_recharge(i)
            if n and i.get("heart_rate_avg"):
                fc[n["date"]] = i["heart_rate_avg"]
        for l in lignes:
            l["fc_repos"] = fc.get(l["date"])
        if progression:
            progression(1.0)
        return pd.DataFrame(lignes, columns=["date", "heures", "score", "fc_repos"])


# ------------------------------------------------------------ normalisation
def duree_iso(txt) -> float:
    """'PT1H2M3.5S' → secondes."""
    if not txt:
        return 0.0
    if isinstance(txt, (int, float)):
        return float(txt)
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", str(txt))
    if not m:
        return 0.0
    j, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return j * 86400 + h * 3600 + mi * 60 + s


def _date(v) -> Optional[date]:
    try:
        return datetime.fromisoformat(str(v)[:19]).date()
    except (TypeError, ValueError):
        try:
            return date.fromisoformat(str(v)[:10])
        except (TypeError, ValueError):
            return None


def normaliser_exercice(e: dict) -> Optional[dict]:
    if not isinstance(e, dict):
        return None
    jour = _date(e.get("start_time"))
    if not jour:
        return None
    sport = f'{e.get("sport", "")} {e.get("detailed_sport_info", "")}'.upper()
    hr = e.get("heart_rate") or {}
    return {
        "id": str(e.get("id", "")), "date": jour, "debut": str(e.get("start_time"))[:19],
        "nom": "Course", "distance_km": round(float(e.get("distance") or 0) / 1000, 3),
        "duree_s": duree_iso(e.get("duration")), "fc_moy": hr.get("average"), "fc_max": hr.get("maximum"),
        "denivele": 0,
        "extras": {k: v for k, v in {"calories": e.get("calories"),
                                     "charge": (e.get("training_load") or None)}.items() if v},
        "sport": "course" if "RUN" in sport else ("velo" if ("CYCL" in sport or "BIK" in sport) else "autre"),
    }


def normaliser_recharge(i: dict) -> Optional[dict]:
    if not isinstance(i, dict):
        return None
    jour = _date(i.get("date"))
    v = i.get("heart_rate_variability_avg")
    if not jour or v is None:
        return None
    return {"date": jour, "nuit": float(v), "moy_7j": None, "zone_basse": None, "zone_haute": None,
            "statut": str(i.get("nightly_recharge_status", ""))}


def normaliser_nuit(i: dict) -> Optional[dict]:
    if not isinstance(i, dict):
        return None
    jour = _date(i.get("date"))
    sec = sum(float(i.get(k) or 0) for k in ("light_sleep", "deep_sleep", "rem_sleep"))
    if not jour or not sec:
        return None
    return {"date": jour, "heures": round(sec / 3600, 2), "score": i.get("sleep_score"), "fc_repos": None}
