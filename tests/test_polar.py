from datetime import date

import pandas as pd

from foulee.data import polar as P
from foulee.data.donnees import rafraichir


def test_duree_iso():
    assert P.duree_iso("PT1H2M3S") == 3723
    assert P.duree_iso("PT45M") == 2700
    assert P.duree_iso("PT2H44M") == 9840
    assert P.duree_iso("PT31M12.5S") == 1872.5


def test_normalisation():
    ex = {"id": "2AC312F", "start_time": "2026-11-05T18:30:02", "duration": "PT45M10S", "distance": 8123.4,
          "heart_rate": {"average": 148, "maximum": 171}, "sport": "RUNNING", "detailed_sport_info": "RUNNING"}
    n = P.normaliser_exercice(ex)
    assert n["sport"] == "course" and n["date"] == date(2026, 11, 5) and n["distance_km"] == 8.123 and n["duree_s"] == 2710
    velo = P.normaliser_exercice({**ex, "sport": "CYCLING", "detailed_sport_info": "ROAD_BIKING"})
    assert velo["sport"] == "velo"
    r = P.normaliser_recharge({"date": "2026-11-06", "heart_rate_variability_avg": 41, "heart_rate_avg": 55})
    assert r["nuit"] == 41.0
    s = P.normaliser_nuit({"date": "2026-11-06", "light_sleep": 14000, "deep_sleep": 5400, "rem_sleep": 6000,
                           "sleep_score": 81})
    assert s["heures"] == round(25400 / 3600, 2)


class FauxPolar(P.ClientPolar):
    """Répond comme l'API Polar, sans réseau."""
    def __init__(self):
        super().__init__({"access_token": "x"})

    def get(self, chemin, params=None, brut=False):
        if chemin == "/v3/exercises":
            return [{"id": "A1", "start_time": "2026-11-05T18:30:02", "duration": "PT40M", "distance": 7000,
                     "heart_rate": {"average": 145, "maximum": 168}, "sport": "RUNNING"},
                    {"id": "B2", "start_time": "2026-11-04T12:00:00", "duration": "PT60M", "distance": 25000,
                     "sport": "CYCLING"}]
        if chemin == "/v3/users/nightly-recharge":
            return {"recharges": [{"date": "2026-11-06", "heart_rate_variability_avg": 44, "heart_rate_avg": 54}]}
        if chemin == "/v3/users/sleep":
            return {"nights": [{"date": "2026-11-06", "light_sleep": 15000, "deep_sleep": 5000, "rem_sleep": 6000,
                                "sleep_score": 80}]}
        return None


def test_rafraichir_avec_polar_accumule():
    c = FauxPolar()
    ancien = {"activites": [{"id": "vieux", "date": "2026-08-01", "debut": "2026-08-01T08:00:00", "nom": "Course",
                             "distance_km": 10.0, "duree_s": 3000, "fc_moy": 150, "fc_max": 170, "denivele": 0}],
              "vfc": [], "sommeil": [], "maj": "2026-08-01T09:00"}
    cache = rafraichir(c, ancien, date(2026, 11, 7))
    ids = {a["id"] for a in cache["activites"]}
    assert ids == {"vieux", "A1", "B2"}    # l'ancien reste, le vélo est gardé
    assert cache["vfc"][0]["nuit"] == 44.0
    assert cache["sommeil"][0]["fc_repos"] == 54
