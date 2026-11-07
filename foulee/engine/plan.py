"""Génération du plan : périodisation à rebours depuis la date de course.

Structure classique (base → développement → spécifique → affûtage), volume
qui progresse d'au plus ~8 %/semaine avec une semaine allégée toutes les 4,
environ 80 % du temps en facile, allures issues du VDOT."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from . import vdot as V
from .velo import FabriqueVelo
from .velo import placer as placer_velo
from .seances import (CONTINU, ECHAUFFEMENT, EFFORT, RECUP, RETOUR, Bloc, Etape, Seance,
                      fmt_duree)

PIC = {"5k": 32, "10k": 42, "semi": 50, "marathon": 65}
LONGUE_MAX = {"5k": 14, "10k": 17, "semi": 21, "marathon": 32}
AFFUTAGE = {"5k": [0.65], "10k": [0.65], "semi": [0.75, 0.55], "marathon": [0.8, 0.65, 0.45]}

# Jour de la semaine (0 = lundi) → rôle : Q = qualité 1, Q2 = qualité 2, E = facile, L = longue
GABARITS = {
    2: {2: "Q", 6: "L"},
    3: {1: "Q", 3: "E", 6: "L"},
    4: {1: "Q", 3: "E", 5: "E", 6: "L"},
    5: {1: "Q", 2: "E", 3: "Q2", 5: "E", 6: "L"},
    6: {0: "E", 1: "Q", 2: "E", 3: "Q2", 5: "E", 6: "L"},
    7: {0: "E", 1: "Q", 2: "E", 3: "Q2", 4: "E", 5: "E", 6: "L"},
}
PHASES = {"base": "Base", "dev": "Développement", "spe": "Spécifique", "aff": "Affûtage"}


@dataclass
class Profil:
    distance: str = "semi"
    date_course: Optional[date] = None
    objectif_s: Optional[int] = None
    courses_semaine: int = 4
    renfo_semaine: int = 2
    sexe: str = ""
    velo_semaine: int = 0
    ftp: Optional[int] = None
    fc_max: Optional[float] = None


@dataclass
class Semaine:
    debut: date
    phase: str
    km: float
    seances: list[Seance]


@dataclass
class Plan:
    semaines: list[Semaine]
    allures: dict
    allure_course: float
    vdot: float

    def seances(self) -> list[Seance]:
        return [s for sem in self.semaines for s in sem.seances]

    def du_jour(self, jour: date) -> list[Seance]:
        return [s for s in self.seances() if s.jour == jour]

    def semaine_de(self, jour: date) -> Optional[Semaine]:
        for sem in self.semaines:
            if sem.debut <= jour < sem.debut + timedelta(days=7):
                return sem
        return None


def lundi(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _mid(fourchette) -> float:
    return (fourchette[0] + fourchette[1]) / 2


def _arrondi5(minutes: float) -> int:
    return max(5, int(5 * round(minutes / 5)))


class _Fabrique:
    """Construit les séances avec les allures de la personne."""

    def __init__(self, allures: dict, allure_course: float, distance: str):
        self.A = allures
        self.ac = allure_course
        self.distance = distance

    def e(self, minutes: int, libelle: str = "Footing") -> Etape:
        lo, hi = self.A["E"]
        return Etape(CONTINU, duree_s=minutes * 60, allure_min=lo, allure_max=hi, libelle=libelle)

    def echauffement(self, minutes=15):
        lo, hi = self.A["E"]
        return Etape(ECHAUFFEMENT, duree_s=minutes * 60, allure_min=lo, allure_max=hi)

    def retour(self, minutes=10):
        lo, hi = self.A["E"]
        return Etape(RETOUR, duree_s=minutes * 60, allure_min=lo, allure_max=hi)

    def km_etape(self, e: Etape) -> float:
        allure = ((e.allure_min or 0) + (e.allure_max or 0)) / 2 or _mid(self.A["E"])
        if e.distance_m:
            return e.distance_m / 1000
        return (e.duree_s or 0) / allure

    def seance(self, jour, genre, titre, blocs, note="") -> Seance:
        km = sum(self.km_etape(e) * b.repetitions for b in blocs for e in b.etapes)
        sec = 0.0
        for b in blocs:
            for e in b.etapes:
                if e.duree_s:
                    sec += e.duree_s * b.repetitions
                else:
                    allure = ((e.allure_min or 0) + (e.allure_max or 0)) / 2 or _mid(self.A["E"])
                    sec += (e.distance_m or 0) / 1000 * allure * b.repetitions
        return Seance(jour, "course", genre, titre, blocs, round(km, 1), int(round(sec / 60)), note)

    # ---- séances types
    def footing(self, jour, minutes, titre="Footing"):
        return self.seance(jour, "footing", f"{titre} · {fmt_duree(minutes * 60, court=True)}", [Bloc([self.e(minutes)])])

    def longue(self, jour, minutes):
        return self.seance(jour, "long", f"Sortie longue · {fmt_duree(minutes * 60, court=True)}",
                           [Bloc([self.e(minutes, "Sortie longue")])],
                           "Allure de conversation. Si tu ne peux plus parler, ralentis.")

    def intervalles(self, jour, genre, titre, n, effort: Etape, recup: Etape, note=""):
        return self.seance(jour, genre, titre,
                           [Bloc([self.echauffement()]), Bloc([effort, recup], n), Bloc([self.retour()])], note)

    def qualite(self, jour, phase: str, slot: str, rang: int) -> Seance:
        A = self.A
        trot = lambda s: Etape(RECUP, duree_s=s, allure_min=A["E"][1], allure_max=A["E"][1] + 60)
        if phase == "base":
            if slot == "Q":
                n = 8 + min(rang, 4)
                return self.intervalles(jour, "cotes", f"Côtes · {n} × 30 s", n,
                                        Etape(EFFORT, duree_s=30, libelle="Montée tonique"),
                                        Etape(RECUP, duree_s=75, libelle="Descente en trottinant"),
                                        "Une côte douce : monte en restant relâchée, redescends tranquille.")
            n = 6 + min(rang, 4)
            return self.intervalles(jour, "fartlek", f"Fartlek · {n} × 1 min", n,
                                    Etape(EFFORT, duree_s=60, allure_min=A["T"][0], allure_max=A["T"][1]),
                                    trot(60), "Du jeu : vite mais relâché, comme quand on court après un bus.")
        if phase == "dev":
            if slot == "Q":
                variantes = [(8, 400, 90), (6, 800, 120), (5, 1000, 150)]
                n, d, r = variantes[rang % 3]
                titre = f"Fractionné · {n} × {d} m"
                return self.intervalles(jour, "vma", titre, n,
                                        Etape(EFFORT, distance_m=d, allure_min=A["I"][0], allure_max=A["I"][1]),
                                        trot(r))
            variantes = [(3, 10, 2), (2, 15, 3), (4, 8, 2)]
            n, m, r = variantes[rang % 3]
            return self.intervalles(jour, "seuil", f"Seuil · {n} × {m} min", n,
                                    Etape(EFFORT, duree_s=m * 60, allure_min=A["T"][0], allure_max=A["T"][1]),
                                    trot(r * 60), "Allure « confortablement difficile » : tu pourrais dire une phrase, pas chanter.")
        if phase == "spe":
            if slot == "Q2" or rang % 2 == 0:
                spec = {"5k": (5, 1000, 120), "10k": (4, 2000, 120), "semi": (3, 3000, 180), "marathon": (2, 6000, 180)}
                n, d, r = spec[self.distance]
                lo, hi = round(self.ac - 3), round(self.ac + 3)
                nom = V.NOMS_DISTANCES[self.distance].lower()
                return self.intervalles(jour, "specifique", f"Allure {nom} · {n} × {d / 1000:g} km", n,
                                        Etape(EFFORT, distance_m=d, allure_min=lo, allure_max=hi),
                                        trot(r), "On apprivoise l'allure du jour J.")
            return self.intervalles(jour, "seuil", "Seuil · 2 × 15 min", 2,
                                    Etape(EFFORT, duree_s=900, allure_min=A["T"][0], allure_max=A["T"][1]),
                                    trot(180))
        # affûtage
        lo, hi = round(self.ac - 3), round(self.ac + 3)
        return self.intervalles(jour, "rappel", "Rappel · 5 × 2 min allure course", 5,
                                Etape(EFFORT, duree_s=120, allure_min=lo, allure_max=hi), trot(90),
                                "Court et vif : on garde les jambes réveillées sans se fatiguer.")

    def jour_j(self, jour, objectif_s):
        d = V.DISTANCES[self.distance]
        lo, hi = round(self.ac - 2), round(self.ac + 2)
        s = self.seance(jour, "course", f"Jour J · {V.NOMS_DISTANCES[self.distance]}",
                        [Bloc([Etape(EFFORT, distance_m=int(d), allure_min=lo, allure_max=hi, libelle="Course")])],
                        "Pars un poil plus lentement que prévu, accélère si tout va bien après la mi-course.")
        s.sport = "course_cible"
        return s


def allure_cible(vdot: float, distance: str, objectif_s: Optional[int]) -> float:
    pred = V.allure_course(vdot, distance)
    if not objectif_s:
        return pred
    obj = objectif_s / (V.DISTANCES[distance] / 1000)
    return max(obj, pred * 0.97)  # jamais plus de 3 % plus vite que ce que ton niveau actuel permet


def generer_plan(profil: Profil, debut: date, vdot: float, volume_depart: float, plus_longue_km: float,
                 facteur_allure: float = 1.0, facteur_volume: float = 1.0) -> Plan:
    if profil.date_course is None:
        profil.date_course = debut + timedelta(weeks=12)
    A = {k: (round(lo * facteur_allure), round(hi * facteur_allure)) for k, (lo, hi) in V.allures(vdot).items()}
    ac = allure_cible(vdot, profil.distance, profil.objectif_s) * facteur_allure
    fab = _Fabrique(A, ac, profil.distance)
    fab_velo = FabriqueVelo(profil.ftp, profil.fc_max)

    n = min(max(profil.courses_semaine, 2), 7)
    gabarit = GABARITS[n]
    premier = lundi(debut)
    nb_sem = max(1, (lundi(profil.date_course) - premier).days // 7 + 1)
    aff = AFFUTAGE[profil.distance][:max(0, nb_sem - 1)]
    construction = nb_sem - len(aff)
    fin_base = math.ceil(construction * 0.35)
    fin_dev = fin_base + math.ceil(construction * 0.35)

    v_depart = max(volume_depart, 3.5 * n)
    pic = max(v_depart, min(PIC[profil.distance], v_depart * 1.7))
    longue_dep = max(plus_longue_km, 6.0)
    part_longue = {2: 0.45, 3: 0.35}.get(n, 0.3)
    e_mid = _mid(A["E"])

    semaines: list[Semaine] = []
    vol_cible = v_depart
    rangs = {"Q": 0, "Q2": 0}
    for i in range(nb_sem):
        debut_sem = premier + timedelta(weeks=i)
        if i >= construction:
            phase = "aff"
            vol = pic * aff[i - construction]
        else:
            phase = "base" if i < fin_base else ("dev" if i < fin_dev else "spe")
            if i > 0 and i % 4 == 3:
                vol = vol_cible * 0.8          # semaine allégée
            else:
                if i > 0:
                    vol_cible = min(pic, vol_cible * 1.08)
                vol = vol_cible
        vol *= facteur_volume

        seances: list[Seance] = []
        nb_q = sum(1 for r in gabarit.values() if r.startswith("Q"))
        # Une seule qualité : on alterne les deux types d'une semaine à l'autre
        roles = dict(gabarit)
        if nb_q == 1 and i % 2 == 1:
            roles = {j: ("Q2" if r == "Q" else r) for j, r in roles.items()}

        # En phase de base, une seule séance de qualité : la 2e devient un footing
        if phase in ("base", "aff") and nb_q == 2:
            roles = {j: ("E" if r == "Q2" else r) for j, r in roles.items()}

        q_km = 0.0
        qualites = {}
        for j, role in roles.items():
            if role.startswith("Q"):
                s = fab.qualite(debut_sem + timedelta(days=j), phase, role, rangs[role])
                rangs[role] += 1
                qualites[j] = s
                q_km += s.km
        # La longue part de ce que tu fais déjà (sans régresser) et progresse doucement
        km_longue = max(vol * part_longue, min(longue_dep * 0.85, vol * 0.42))
        km_longue = min(LONGUE_MAX[profil.distance], km_longue, longue_dep * 1.1 + 1.0 * i)
        if phase == "aff":
            km_longue = min(km_longue, vol * part_longue)
        km_longue = max(km_longue, 6.0)
        nb_e = sum(1 for r in roles.values() if r == "E")
        km_e = max(4.0, min(14.0, km_longue * 0.7, (vol - km_longue - q_km) / nb_e)) if nb_e else 0

        for j in sorted(roles):
            jour = debut_sem + timedelta(days=j)
            if jour < debut or jour >= profil.date_course:
                continue
            role = roles[j]
            if role.startswith("Q"):
                if 0 < (profil.date_course - jour).days <= 2:
                    seances.append(fab.footing(jour, 20, "Footing + 4 lignes droites"))
                else:
                    seances.append(qualites[j])
            elif role == "L":
                if (profil.date_course - jour).days <= 6:
                    seances.append(fab.footing(jour, _arrondi5(min(km_longue, 10) * e_mid / 60)))
                else:
                    seances.append(fab.longue(jour, _arrondi5(km_longue * e_mid / 60)))
            else:
                if 0 < (profil.date_course - jour).days <= 1:
                    continue  # veille de course : repos
                seances.append(fab.footing(jour, _arrondi5(km_e * e_mid / 60)))

        if debut_sem <= profil.date_course < debut_sem + timedelta(days=7):
            seances.append(fab.jour_j(profil.date_course, profil.objectif_s))

        seances += _placer_renfo(seances, debut_sem, profil, debut)
        seances += placer_velo(seances, debut_sem, profil.velo_semaine, phase, n, debut,
                               profil.date_course, fab_velo)
        ordre = {"course": 0, "course_cible": 0, "velo": 1, "renfo": 2}
        seances.sort(key=lambda s: (s.jour, ordre.get(s.sport, 3)))
        semaines.append(Semaine(debut_sem, phase, round(sum(s.km for s in seances), 1), seances))

    plan = Plan(semaines, A, ac, vdot)
    plan.ftp, plan.fc_max = profil.ftp, profil.fc_max
    return plan


def _placer_renfo(seances: list[Seance], debut_sem: date, profil: Profil, debut: date) -> list[Seance]:
    r = min(max(profil.renfo_semaine, 0), 3)
    if r == 0:
        return []
    dures = {s.jour for s in seances if s.genre not in ("footing",)}
    tres_dures = {s.jour for s in seances if s.genre in ("long", "course")}
    faciles = {s.jour for s in seances if s.genre == "footing"}
    jours = [debut_sem + timedelta(days=k) for k in range(7)]

    def avant_course(j: date) -> bool:
        return profil.date_course is None or (profil.date_course - j).days > 3

    def ok(j: date) -> bool:
        return j >= debut and j not in dures and (j + timedelta(days=1)) not in dures and avant_course(j)

    def ok_qualite(j: date) -> bool:
        # Repli « jours durs durs » : renfo juste après une séance de qualité
        return (j >= debut and j in dures and j not in tres_dures
                and (j + timedelta(days=1)) not in tres_dures and avant_course(j))

    candidats = ([j for j in jours if ok(j) and j in faciles] + [j for j in jours if ok(j) and j not in faciles]
                 + [j for j in jours if ok_qualite(j)])
    choisis: list[date] = []
    for j in candidats:
        if len(choisis) >= r:
            break
        if all(abs((j - c).days) >= 2 for c in choisis):
            choisis.append(j)
    return [Seance(j, "renfo", "renfo", "Renfo", [], 0.0, 20) for j in choisis]
