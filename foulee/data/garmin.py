"""Client de l'API Garmin Connect Personal (lecture seule, tes propres données).

Points d'accès d'après le client officiel garmin/connect-personal-api-python.
La clé personnelle s'échange contre un jeton valable 24 h."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

import pandas as pd
import requests

from .metriques import garmin_activite, garmin_quotidien

BASE_URL = "https://personal.connectapi.garmin.com"
JETON = "/personalapitoken-service/personal-api/personal-api-key/token"
TYPES_VELO = {"cycling", "indoor_cycling", "virtual_ride", "road_biking", "mountain_biking", "gravel_cycling",
              "e_bike_fitness", "track_cycling", "cyclocross"}
TYPES_COURSE = {"running", "trail_running", "treadmill_running", "track_running", "street_running",
                "indoor_running", "virtual_run", "ultra_run"}


class GarminErreur(Exception):
    pass


class ClientGarmin:
    def __init__(self, cle: str, session: Optional[requests.Session] = None):
        if not cle:
            raise GarminErreur("Clé Garmin manquante.")
        self.cle = nettoyer_cle(cle)
        self.http = session or requests.Session()
        self.http.headers.update({"User-Agent": "Foulee/0.3 (usage personnel)"})
        self._jeton: Optional[str] = None
        self._expire = 0.0

    # ------------------------------------------------------------ bas niveau
    def jeton(self) -> str:
        if self._jeton and time.time() < self._expire - 300:
            return self._jeton
        r = self.http.post(BASE_URL + JETON, timeout=30,
                           headers={"Authorization": f"ApiKey {self.cle}", "Accept": "application/json, text/plain, */*"})
        if r.status_code in (401, 403):
            raise GarminErreur("Garmin refuse la clé : elle a peut-être expiré ou été supprimée. "
                               "Crée-en une nouvelle dans Garmin Connect (web) › Paramètres › Personal API.")
        if not r.ok:
            raise GarminErreur(f"Garmin refuse la demande de jeton (code {r.status_code}). "
                               f"Vérifie que tu as collé la clé entière, sans espace ni guillemet. "
                               f"Réponse de Garmin : {self._extrait(r)}")
        jeton, duree = lire_jeton(r)
        if not jeton:
            raise GarminErreur(f"Réponse inattendue de Garmin lors de l'authentification : {self._extrait(r)}")
        self._jeton = jeton
        self._expire = time.time() + duree
        return jeton

    def _extrait(self, r) -> str:
        """Début de la réponse, sans jamais réafficher la clé."""
        txt = (r.text or "").replace(self.cle, "•••")[:200].strip()
        return txt or "(vide)"

    def get(self, chemin: str, params: Optional[dict] = None, brut: bool = False) -> Any:
        for essai in range(3):
            r = self.http.get(BASE_URL + chemin, params=params, timeout=60,
                              headers={"Authorization": f"Bearer {self.jeton()}"})
            if r.status_code == 429:
                time.sleep(2 * (essai + 1))
                continue
            if r.status_code == 401 and essai == 0:
                self._jeton = None
                continue
            if r.status_code == 404:
                return None
            if not r.ok:
                raise GarminErreur(f"Erreur Garmin {r.status_code} sur {chemin}")
            if brut:
                return r.content
            return r.json() if r.content else None
        raise GarminErreur("Garmin limite le nombre de requêtes, réessaie dans une minute.")

    def verifier(self) -> bool:
        self.jeton()
        return True

    # ------------------------------------------------------------ activités
    def activites(self, debut: date, fin: date) -> pd.DataFrame:
        lignes, depart = [], 0
        while True:
            lot = self.get("/activitylist-service/activities/search/activities",
                           {"start": depart, "limit": 100, "startDate": debut.isoformat(), "endDate": fin.isoformat()})
            if not lot:
                break
            if isinstance(lot, dict):
                lot = lot.get("activityList") or lot.get("activities") or []
            lignes += [normaliser_activite(a) for a in lot]
            if len(lot) < 100:
                break
            depart += 100
        df = pd.DataFrame([l for l in lignes if l])
        if df.empty:
            return df
        return df[df["sport"] != "autre"].sort_values("debut").reset_index(drop=True)

    def fichier_activite(self, activite_id) -> Optional[bytes]:
        return self.get(f"/download-service/files/activity/{activite_id}", brut=True)

    # ------------------------------------------------------------ santé
    def vfc(self, debut: date, fin: date) -> pd.DataFrame:
        lignes = []
        d = debut
        while d <= fin:
            f = min(d + timedelta(days=27), fin)
            rep = self.get(f"/hrv-service/hrv/daily/{d.isoformat()}/{f.isoformat()}")
            items = []
            if isinstance(rep, dict):
                items = rep.get("hrvSummaries") or rep.get("hrvSummaryList") or rep.get("summaries") or []
            elif isinstance(rep, list):
                items = rep
            lignes += [x for x in (normaliser_vfc(i) for i in items) if x]
            d = f + timedelta(days=1)
        return pd.DataFrame(lignes, columns=["date", "nuit", "moy_7j", "zone_basse", "zone_haute", "statut"])

    def quotidien(self, debut: date, fin: date) -> pd.DataFrame:
        """Résumés quotidiens : pas, Body Battery, stress, FC repos, SpO2… (selon la montre)."""
        lignes = []
        d = debut
        while d <= fin:
            f = min(d + timedelta(days=30), fin)
            rep = self.get("/usersummary-service/v2/dailysummaries",
                           {"startDate": d.isoformat(), "endDate": f.isoformat()})
            items = rep if isinstance(rep, list) else []
            if isinstance(rep, dict):
                items = (rep.get("dailySummaries") or rep.get("summaries") or rep.get("userDailySummaries")
                         or ([rep] if "calendarDate" in rep else []))
            for it in items:
                jour = _date(_get(it, "calendarDate", "date")) if isinstance(it, dict) else None
                if jour:
                    m = garmin_quotidien(it)
                    if m:
                        lignes.append({"date": jour, **m})
            d = f + timedelta(days=1)
        df = pd.DataFrame(lignes)
        # FC au repos : si le résumé du jour ne la donne pas, on la lit dans la FC du jour (14 derniers jours)
        manque = df.empty or "fc_repos" not in df or df["fc_repos"].dropna().empty
        if manque:
            rhr = self.fc_repos_jours([fin - timedelta(days=k) for k in range(min(14, (fin - debut).days + 1))])
            if rhr:
                extra = pd.DataFrame([{"date": j, "fc_repos": v} for j, v in rhr.items()])
                df = extra if df.empty else df.drop(columns=["fc_repos"], errors="ignore").merge(extra, on="date", how="outer")
        return df

    def fc_repos_jours(self, jours: list[date]) -> dict:
        def un(j):
            try:
                rep = self.get("/wellness-service/wellness/dailyHeartRate", {"date": j.isoformat()})
            except GarminErreur:
                return j, None
            if isinstance(rep, dict):
                return j, _get(rep, "restingHeartRate", "restingHeartRateValue", "lastSevenDaysAvgRestingHeartRate")
            return j, None
        with ThreadPoolExecutor(max_workers=4) as pool:
            return {j: float(v) for j, v in pool.map(un, jours) if v}

    def sommeil(self, jours: list[date], progression: Optional[Callable[[float], None]] = None) -> pd.DataFrame:
        def un_jour(j):
            try:
                return normaliser_sommeil(j, self.get("/sleep-service/sleep/dailySleep", {"date": j.isoformat()}))
            except GarminErreur:
                return None
        self.jeton()
        lignes = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            for k, res in enumerate(pool.map(un_jour, jours)):
                if res:
                    lignes.append(res)
                if progression and jours:
                    progression((k + 1) / len(jours))
        return pd.DataFrame(lignes, columns=["date", "heures", "score", "fc_repos"])


def nettoyer_cle(cle: str) -> str:
    """Retire ce qu'on colle souvent par erreur autour de la clé."""
    c = (cle or "").strip().strip('"').strip("'").strip()
    if c.lower().startswith("apikey"):
        c = c[6:].strip(" :")
    c = c.strip("[]<>").strip()
    return "".join(c.split())  # aucun espace ni retour à la ligne à l'intérieur


def lire_jeton(r) -> tuple[Optional[str], float]:
    """Garmin peut renvoyer le jeton en JSON ou en texte brut."""
    try:
        corps = r.json()
    except ValueError:
        corps = None
    if isinstance(corps, dict):
        j = corps.get("access_token") or corps.get("accessToken") or corps.get("token")
        return j, float(corps.get("expires_in") or corps.get("expiresIn") or 86400)
    if isinstance(corps, str) and corps:
        return corps.strip(), 86400.0
    texte = (r.text or "").strip().strip('"')
    if texte and " " not in texte and len(texte) > 20:
        return texte, 86400.0
    return None, 0.0


# ------------------------------------------------------------ normalisation
def _date(v) -> Optional[date]:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "")[:19]).date()
    except ValueError:
        try:
            return date.fromisoformat(str(v)[:10])
        except ValueError:
            return None


def _get(d: dict, *cles, defaut=None):
    for c in cles:
        cur = d
        for morceau in c.split("."):
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(morceau)
        if cur not in (None, ""):
            return cur
    return defaut


def normaliser_activite(a: dict) -> Optional[dict]:
    if not isinstance(a, dict):
        return None
    type_cle = str(_get(a, "activityType.typeKey", "activityTypeDTO.typeKey", "activityType", defaut="")).lower()
    debut = _get(a, "startTimeLocal", "startTimeGMT", "beginTimestamp", "startTime")
    if isinstance(debut, (int, float)):
        debut = datetime.fromtimestamp(debut / 1000).isoformat()
    jour = _date(debut)
    if not jour:
        return None
    dist = float(_get(a, "distance", "summaryDTO.distance", defaut=0) or 0)
    duree = float(_get(a, "movingDuration", "duration", "elapsedDuration", "summaryDTO.duration", defaut=0) or 0)
    if duree > 100000:  # certaines réponses en millisecondes
        duree /= 1000
    return {
        "id": str(_get(a, "activityId", "id", defaut="")),
        "date": jour,
        "debut": str(debut)[:19],
        "nom": _get(a, "activityName", defaut="Course"),
        "distance_km": round(dist / 1000, 3),
        "duree_s": duree,
        "fc_moy": _get(a, "averageHR", "averageHeartRate", "summaryDTO.averageHR"),
        "fc_max": _get(a, "maxHR", "maxHeartRate", "summaryDTO.maxHR"),
        "denivele": _get(a, "elevationGain", "summaryDTO.elevationGain", defaut=0),
        "extras": garmin_activite(a),
        "sport": ("course" if type_cle in TYPES_COURSE or "run" in type_cle
                  else "velo" if type_cle in TYPES_VELO or "cycl" in type_cle or "bik" in type_cle or "ride" in type_cle
                  else "autre"),
    }


def normaliser_vfc(i: dict) -> Optional[dict]:
    if not isinstance(i, dict):
        return None
    jour = _date(_get(i, "calendarDate", "date"))
    nuit = _get(i, "lastNightAvg", "lastNightAverage", "hrvSummary.lastNightAvg")
    if not jour or nuit is None:
        return None
    return {
        "date": jour, "nuit": float(nuit),
        "moy_7j": _get(i, "weeklyAvg", "weeklyAverage"),
        "zone_basse": _get(i, "baseline.balancedLow", "baselineBalancedLow"),
        "zone_haute": _get(i, "baseline.balancedUpper", "baselineBalancedUpper"),
        "statut": _get(i, "status", defaut=""),
    }


def normaliser_sommeil(jour: date, rep: Optional[dict]) -> Optional[dict]:
    if not isinstance(rep, dict):
        return None
    dto = rep.get("dailySleepDTO") or rep
    sec = _get(dto, "sleepTimeSeconds", "totalSleepSeconds")
    if not sec:
        return None
    return {
        "date": jour,
        "heures": round(float(sec) / 3600, 2),
        "score": _get(dto, "sleepScores.overall.value", "sleepScore", "overallSleepScore.value"),
        "fc_repos": _get(rep, "restingHeartRate", "dailySleepDTO.restingHeartRate"),
    }
