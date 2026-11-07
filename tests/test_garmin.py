import json

import pytest

from foulee.data import garmin as G


class Rep:
    def __init__(self, code, texte, ctype="text/plain"):
        self.status_code, self.text = code, texte
        self.content = texte.encode()
        self.ok = 200 <= code < 300

    def json(self):
        return json.loads(self.text)


class Session:
    def __init__(self, rep):
        self.rep, self.headers, self.vu = rep, {}, None

    def post(self, url, headers=None, timeout=None):
        self.vu = headers
        return self.rep


def test_nettoyer_cle():
    assert G.nettoyer_cle('  "abc123"  ') == "abc123"
    assert G.nettoyer_cle("ApiKey abc123") == "abc123"
    assert G.nettoyer_cle("[abc123]") == "abc123"
    assert G.nettoyer_cle("abc\n123 ") == "abc123"


@pytest.mark.parametrize("corps", ['eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature_assez_longue',
                                   '{"access_token": "eyJabc.def.ghi_longue_valeur", "expires_in": 86400}',
                                   '"eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature"'])
def test_jeton_texte_ou_json(corps):
    s = Session(Rep(200, corps))
    c = G.ClientGarmin("[ma-cle]", session=s)
    j = c.jeton()
    assert j.startswith("eyJ")
    assert s.vu["Authorization"] == "ApiKey ma-cle"


def test_erreur_400_explique_sans_montrer_la_cle():
    s = Session(Rep(400, '{"message":"Invalid API key ma-cle"}'))
    c = G.ClientGarmin("ma-cle", session=s)
    with pytest.raises(G.GarminErreur) as e:
        c.jeton()
    assert "400" in str(e.value) and "ma-cle" not in str(e.value) and "Invalid API key" in str(e.value)


def test_url_supabase_tolerante():
    from foulee.data.store import StockageSupabase
    for u in ("https://abc.supabase.co", "https://abc.supabase.co/", "https://abc.supabase.co/rest/v1/",
              " https://abc.supabase.co/rest/v1 "):
        assert StockageSupabase(u, "sb_secret_x").url == "https://abc.supabase.co/rest/v1/foulee"


def test_mesures_bonus_garmin():
    from foulee.data.metriques import formater, garmin_activite, garmin_quotidien
    q = garmin_quotidien({"calendarDate": "2026-11-06", "totalSteps": 11234, "bodyBatteryHighestValue": 88,
                          "restingHeartRate": 48, "moderateIntensityMinutes": 20, "vigorousIntensityMinutes": 15,
                          "averageSpo2": None})
    assert q == {"pas": 11234, "bb_max": 88, "fc_repos": 48, "intensite": 50}
    a = garmin_activite({"averageRunningCadenceInStepsPerMinute": 172.4, "aerobicTrainingEffect": 3.6,
                         "avgStrideLength": 112.0, "avgPower": None, "avgGroundContactTime": 0})
    assert a == {"cadence": 172.4, "te_aerobie": 3.6, "foulee": 1.12}
    assert formater("pas", 11234) == "11 234"
    assert formater("te_aerobie", 3.6).startswith("3,6")


def test_garmin_quotidien_client():
    class C(G.ClientGarmin):
        def __init__(self):
            pass

        def get(self, chemin, params=None, brut=False):
            assert chemin == "/usersummary-service/v2/dailysummaries"
            return [{"calendarDate": params["startDate"], "totalSteps": 9000, "averageStressLevel": 30}]
    from datetime import date
    df = C().quotidien(date(2026, 9, 1), date(2026, 11, 6))
    assert len(df) == 3 and set(df.columns) == {"date", "pas", "stress"}
