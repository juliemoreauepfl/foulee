from datetime import datetime, timezone

from foulee.data.fitfile import BASE, EPOQUE_FIT, RECORD, _Ecrivain, lire_flux
from foulee.engine import cardio as CA


def _fit_activite(n=1800, fc=lambda t: 140, v=3.0):
    """Petit fichier d'activité FIT avec des records toutes les secondes."""
    from foulee.data import fitfile as F
    w = _Ecrivain()
    t0 = int((datetime(2026, 11, 7, 8, tzinfo=timezone.utc) - EPOQUE_FIT).total_seconds())
    w.message(0, F.FILE_ID, [(0, F.ENUM, 1, 4), (4, F.UINT32, 4, t0)])
    for t in range(n):
        w.message(1, RECORD, [(253, F.UINT32, 4, t0 + t), (3, F.UINT8, 1, fc(t)),
                              (5, F.UINT32, 4, int(v * t * 100)), (6, F.UINT16, 2, int(v * 1000))])
    return w.fichier()


def test_lire_flux():
    flux = lire_flux(_fit_activite(600, fc=lambda t: 120 + t // 60))
    assert len(flux) == 120 and flux[0]["t"] == 0 and flux[-1]["t"] == 595
    assert flux[10]["fc"] == 120 and abs(flux[10]["v"] - 3.0) < 1e-6 and flux[-1]["d"] > 1700


def test_zones_et_footing_trop_rapide():
    b = CA.bornes(190, 50)
    assert b == [120, 134, 148, 162, 176, 190]
    lent = CA.analyser(lire_flux(_fit_activite(2400, fc=lambda t: 140)), 190, 50, "footing")
    assert lent.pct[1] == 100 and lent.messages[0][0] == "ok"
    vite = CA.analyser(lire_flux(_fit_activite(2400, fc=lambda t: 158)), 190, 50, "footing")
    assert vite.pct[2] == 100 and vite.messages[0][0] == "attention"


def test_derive_cardiaque():
    stable = CA.analyser(lire_flux(_fit_activite(3600, fc=lambda t: 140)), 190, 50, "long")
    assert stable.derive is not None and abs(stable.derive) < 1
    derive = CA.analyser(lire_flux(_fit_activite(3600, fc=lambda t: 132 + t // 150)), 190, 50, "long")
    assert derive.derive > 5 and any("Dérive" in m for _, m in derive.messages)


def test_pas_de_fc():
    assert CA.analyser([], 190, 50) is None
