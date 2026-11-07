"""Import de sorties depuis des fichiers .FIT ou .GPX (sans clé Garmin)."""
from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

from .fitfile import EPOQUE_FIT, SESSION, extraire_fit, lire_messages


def depuis_fit(contenu: bytes, nom: str = "") -> Optional[dict]:
    msgs = lire_messages(extraire_fit(contenu))
    sess = next((v for g, v in msgs if g == SESSION), None)
    if not sess:
        return None
    debut = sess.get(2)  # start_time
    if debut is None:
        return None
    dt = (EPOQUE_FIT + timedelta(seconds=debut)).astimezone()
    sport = sess.get(5)
    if sport not in (None, 1, 2):  # 1 = course à pied, 2 = vélo
        return None
    s = _sortie(contenu, dt, (sess.get(9) or 0) / 100, (sess.get(8) or sess.get(7) or 0) / 1000,
                sess.get(16), sess.get(17), "Vélo importé" if sport == 2 else nom)
    if s:
        s["sport"] = "velo" if sport == 2 else "course"
    return s


def _haversine(a, b):
    r = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def depuis_gpx(contenu: bytes, nom: str = "") -> Optional[dict]:
    racine = ET.fromstring(contenu)
    pts, temps, fcs = [], [], []
    for el in racine.iter():
        if el.tag.endswith("trkpt"):
            pts.append((float(el.get("lat")), float(el.get("lon"))))
            t = next((c.text for c in el if c.tag.endswith("time")), None)
            temps.append(datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None)
            fc = next((c.text for c in el.iter() if c.tag.endswith("hr")), None)
            if fc:
                fcs.append(int(fc))
    temps = [t for t in temps if t]
    if len(pts) < 2 or len(temps) < 2:
        return None
    dist = sum(_haversine(a, b) for a, b in zip(pts, pts[1:]))
    duree = (temps[-1] - temps[0]).total_seconds()
    fc_moy = round(sum(fcs) / len(fcs)) if fcs else None
    return _sortie(contenu, temps[0].astimezone(), dist, duree, fc_moy, max(fcs) if fcs else None, nom)


def _sortie(contenu, dt, dist_m, duree_s, fc_moy, fc_max, nom):
    if dist_m < 500 or duree_s < 120:
        return None
    return {"id": "fichier-" + hashlib.sha1(contenu).hexdigest()[:12], "date": dt.date().isoformat(),
            "debut": dt.replace(tzinfo=None).isoformat(timespec="seconds"), "nom": nom or "Course importée",
            "distance_km": round(dist_m / 1000, 2), "duree_s": round(duree_s), "fc_moy": fc_moy,
            "fc_max": fc_max, "denivele": 0, "sport": "course"}


def importer(nom_fichier: str, contenu: bytes) -> Optional[dict]:
    n = nom_fichier.lower()
    if n.endswith(".gpx"):
        return depuis_gpx(contenu, "Course importée")
    if n.endswith(".fit") or n.endswith(".zip"):
        return depuis_fit(contenu, "Course importée")
    return None
