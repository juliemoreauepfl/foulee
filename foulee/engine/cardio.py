"""Ta fréquence cardiaque pendant la sortie : zones, dérive, verdict.

- Zones de Karvonen (% de la FC de réserve = FC max − FC repos) :
  Z1 récup < 60 %, Z2 endurance 60-70 %, Z3 tempo 70-80 %, Z4 seuil 80-90 %, Z5 VMA > 90 %.
- Dérive cardiaque (« découplage ») : sur une sortie régulière, on compare
  vitesse ÷ FC entre la 1re et la 2e moitié (échauffement exclu). Sous 5 % :
  ton endurance encaisse la durée. Au-dessus : chaleur, hydratation, fatigue,
  ou endurance encore à construire."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

NOMS_ZONES = ["Récup", "Endurance", "Tempo", "Seuil", "VMA"]
SEUILS = [0.5, 0.6, 0.7, 0.8, 0.9]           # % de la FC de réserve, bas de chaque zone
FACILES = {"footing", "long", "velo_endurance", "velo_recup"}
QUALITE = {"cotes", "fartlek", "vma", "seuil", "specifique", "rappel", "velo_tempo"}


def bornes(fc_max: float, fc_repos: float) -> list[float]:
    """FC au bas de Z1..Z5, puis FC max."""
    r = fc_max - fc_repos
    return [round(fc_repos + s * r) for s in SEUILS] + [round(fc_max)]


def zone_de(fc: float, b: list[float]) -> int:
    """0..4 (Z1..Z5)."""
    for k in range(4, 0, -1):
        if fc >= b[k]:
            return k
    return 0


@dataclass
class AnalyseFC:
    fc_moy: int
    fc_pic: int
    bornes: list
    secondes: list                           # temps passé dans chaque zone
    pct: list                                # en %
    derive: Optional[float] = None           # en %, positif = la FC a monté à vitesse égale
    efficacite: Optional[float] = None       # mètres par battement au-dessus du repos (plus haut = mieux)
    messages: list = field(default_factory=list)   # (ton, texte) ; ton : ok / attention / info
    points: list = field(default_factory=list)     # (t, fc) pour la courbe

    def resume(self) -> dict:
        return {"fc_moy": self.fc_moy, "fc_pic": self.fc_pic, "pct": self.pct,
                "derive": self.derive, "efficacite": self.efficacite, "messages": self.messages}


def _moyenne(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def derive_cardiaque(flux: list[dict], echauffement_s: int = 600) -> Optional[float]:
    pts = [p for p in flux if p.get("fc") and p.get("v") and p["v"] > 0.5 and p["t"] >= echauffement_s]
    if len(pts) < 40 or pts[-1]["t"] - pts[0]["t"] < 1200:
        return None
    milieu = (pts[0]["t"] + pts[-1]["t"]) / 2
    a = [p for p in pts if p["t"] < milieu]
    b = [p for p in pts if p["t"] >= milieu]
    ef1 = _moyenne([p["v"] for p in a]) / _moyenne([p["fc"] for p in a])
    ef2 = _moyenne([p["v"] for p in b]) / _moyenne([p["fc"] for p in b])
    return round((ef1 - ef2) / ef1 * 100, 1)


def efficacite(flux: list[dict], fc_repos: float, echauffement_s: int = 600) -> Optional[float]:
    """Distance parcourue par battement au-dessus du repos, échauffement exclu.
    À intensité facile, elle monte quand l'endurance progresse et baisse avec la fatigue."""
    pts = [p for p in flux if p.get("fc") and p.get("v") and p["v"] > 0.5 and p["t"] >= echauffement_s]
    if len(pts) < 30:
        return None
    v = _moyenne([p["v"] for p in pts]) * 60
    fc = _moyenne([p["fc"] for p in pts]) - fc_repos
    return round(v / fc, 3) if fc > 5 else None


CIBLES = {  # genre -> (zone basse, zone haute) en indices 0..4
    "footing": (1, 1), "long": (1, 1), "velo_endurance": (1, 1), "velo_recup": (0, 0),
    "seuil": (3, 3), "velo_tempo": (2, 3), "specifique": (2, 3), "fartlek": (2, 3), "rappel": (2, 2),
    "vma": (4, 4), "cotes": (3, 4),
}


def cible(genre: str, b: list) -> Optional[tuple[int, int, str]]:
    """FC visée pendant la séance (bas, haut, texte)."""
    z = CIBLES.get(genre)
    if not z:
        return None
    lo, hi = b[z[0]], b[z[1] + 1]
    zones = f"Z{z[0] + 1}" if z[0] == z[1] else f"Z{z[0] + 1}-Z{z[1] + 1}"
    if genre in ("vma", "cotes"):
        return lo, hi, f"Sur les efforts, au-dessus de {lo} bpm ({zones}). La FC monte en retard : fie-toi d'abord à l'allure."
    if genre in ("footing", "long", "velo_endurance", "velo_recup"):
        return lo, hi, f"Reste sous {hi} bpm ({zones}) tout du long, même si l'allure paraît lente."
    return lo, hi, f"Sur les blocs d'effort : {lo}–{hi} bpm ({zones})."


def analyser(flux: list[dict], fc_max: float, fc_repos: float, genre: str = "footing") -> Optional[AnalyseFC]:
    pts = [p for p in flux if p.get("fc") and 30 < p["fc"] < 230]
    if len(pts) < 20:
        return None
    b = bornes(fc_max, fc_repos)
    sec = [0.0] * 5
    for p, q in zip(pts, pts[1:]):
        dt = min(q["t"] - p["t"], 30)  # pause : on ne compte pas le trou
        sec[zone_de(p["fc"], b)] += dt
    total = sum(sec) or 1
    pct = [round(100 * s / total) for s in sec]
    fc_moy = round(_moyenne([p["fc"] for p in pts]))
    fc_pic = max(p["fc"] for p in pts)
    an = AnalyseFC(fc_moy, fc_pic, b, [round(s) for s in sec], pct)
    an.efficacite = efficacite(flux, fc_repos)
    pas = max(1, len(pts) // 160)
    an.points = [(p["t"], p["fc"]) for p in pts[::pas]]
    m = an.messages

    haut = pct[2] + pct[3] + pct[4]
    if genre in FACILES:
        an.derive = derive_cardiaque(flux)
        if haut > 30:
            m.append(("attention", f"Un peu vite pour de l'endurance : {haut} % du temps au-dessus de {b[2]} bpm. "
                                   "Ralentis jusqu'à pouvoir parler : c'est là que l'endurance se construit."))
        else:
            m.append(("ok", f"Bien dosé : {pct[0] + pct[1]} % du temps en récup ou endurance (sous {b[2]} bpm)."))
        if an.derive is not None:
            if an.derive > 5:
                m.append(("attention", f"Dérive cardiaque de {an.derive:.0f} % : à vitesse égale, ta FC a monté en 2e moitié. "
                                       "Chaleur, hydratation ou fatigue ; ça s'améliore avec les sorties longues."))
            elif an.derive < 3:
                m.append(("ok", f"FC stable d'un bout à l'autre (dérive {max(an.derive, 0):.0f} %) : belle endurance."))
    elif genre in QUALITE:
        intense = pct[3] + pct[4]
        if intense < 8:
            m.append(("info", f"Seulement {intense} % du temps en zone seuil ou VMA : sur les efforts courts, "
                              "la FC n'a pas le temps de monter, c'est normal. Fie-toi aux allures."))
        else:
            m.append(("ok", f"{fmt_min(sec[3] + sec[4])} en zone seuil ou VMA, pic à {fc_pic} bpm : "
                            "le cœur a bien travaillé."))
        if fc_pic >= fc_max * 0.98:
            m.append(("info", f"Tu as touché ta FC max ({fc_pic} bpm). Garde ça pour les vraies séances VMA."))
    else:
        m.append(("info", f"FC moyenne {fc_moy} bpm, pic à {fc_pic} bpm."))
    return an


def fmt_min(s: float) -> str:
    s = int(round(s))
    return f"{s // 60} min" if s >= 60 else f"{s} s"
