"""Séances de vélo / home trainer en complément de la course à pied.

Objectif : du volume aérobie en plus, sans impact. Cibles en % de FTP
(zones de Coggan) pour le home trainer, et repère cardio pour dehors."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .seances import CONTINU, ECHAUFFEMENT, EFFORT, RECUP, RETOUR, Bloc, Etape, Seance, fmt_duree

# Zones de puissance (fraction de FTP) et repères cardio (fraction de FC max)
Z = {"recup": (0.45, 0.55), "endurance": (0.56, 0.72), "tempo": (0.76, 0.87), "sweetspot": (0.88, 0.93)}
FC = {"recup": (0.55, 0.65), "endurance": (0.63, 0.75), "tempo": (0.76, 0.84), "sweetspot": (0.82, 0.88)}


class FabriqueVelo:
    def __init__(self, ftp: Optional[int], fc_max: Optional[float]):
        self.ftp = ftp
        self.fc_max = fc_max

    def etape(self, type_, minutes, zone, libelle=""):
        lo, hi = Z[zone]
        e = Etape(type_, duree_s=int(minutes * 60), puissance_min=lo, puissance_max=hi, libelle=libelle)
        if self.ftp:
            e.watts_min, e.watts_max = round(self.ftp * lo / 5) * 5, round(self.ftp * hi / 5) * 5
        if self.fc_max:
            e.fc_min, e.fc_max = round(self.fc_max * FC[zone][0]), round(self.fc_max * FC[zone][1])
        return e

    def _seance(self, jour, genre, titre, blocs, note):
        minutes = sum((e.duree_s or 0) * b.repetitions for b in blocs for e in b.etapes) // 60
        return Seance(jour, "velo", genre, titre, blocs, 0.0, int(minutes), note)

    def endurance(self, jour: date, minutes: int) -> Seance:
        corps = max(minutes - 15, 10)
        return self._seance(jour, "velo_endurance", f"Vélo endurance · {fmt_duree(minutes * 60, court=True)}",
                            [Bloc([self.etape(ECHAUFFEMENT, 10, "recup")]),
                             Bloc([self.etape(CONTINU, corps, "endurance", "Endurance")]),
                             Bloc([self.etape(RETOUR, 5, "recup")])],
                            "Pédalage souple (85-95 tours/min). Tu dois pouvoir discuter : c'est de l'endurance gratuite pour tes jambes de coureuse ou coureur.")

    def tempo(self, jour: date, n: int = 3, minutes: int = 8) -> Seance:
        return self._seance(jour, "velo_tempo", f"Vélo sweet spot · {n} × {minutes} min",
                            [Bloc([self.etape(ECHAUFFEMENT, 12, "endurance")]),
                             Bloc([self.etape(EFFORT, minutes, "sweetspot", "Sweet spot"),
                                   self.etape(RECUP, 4, "recup", "Récup en souplesse")], n),
                             Bloc([self.etape(RETOUR, 8, "recup")])],
                            "Soutenu mais tenable : ça muscle le moteur sans marteler les jambes.")

    def recup(self, jour: date, minutes: int = 30) -> Seance:
        return self._seance(jour, "velo_recup", f"Vélo récup · {minutes} min",
                            [Bloc([self.etape(CONTINU, minutes, "recup", "Tourner les jambes")])],
                            "Tout en douceur : on fait circuler, on ne force pas.")

    def remplacer_footing(self, s: Seance) -> Seance:
        """Même durée qu'un footing, sans impact (douleur)."""
        v = self.endurance(s.jour, max(30, int(s.minutes * 1.15)))
        v.allegee = True
        return v


def placer(seances: list[Seance], debut_sem: date, n: int, phase: str, nb_courses: int,
           debut: date, date_course: Optional[date], fab: FabriqueVelo) -> list[Seance]:
    """Place n séances de vélo : jours sans course d'abord, jamais la veille d'une séance
    dure ni en fin d'affûtage. Durée selon la phase."""
    n = min(max(n, 0), 3)
    if n == 0:
        return []
    par_jour = {}
    for s in seances:
        par_jour.setdefault(s.jour, []).append(s)
    dures = {s.jour for s in seances if s.sport in ("course", "course_cible") and s.genre != "footing"}

    def ok(j: date) -> bool:
        if j < debut or j in dures:
            return False
        if date_course and (date_course - j).days <= 1:
            return False
        return True

    jours = [debut_sem + timedelta(days=k) for k in range(7)]
    sans_course = [j for j in jours if ok(j) and not any(s.sport == "course" for s in par_jour.get(j, []))]
    avec_footing = [j for j in jours if ok(j) and j not in sans_course]
    choisis: list[date] = []
    for j in sans_course + avec_footing:
        if len(choisis) >= n:
            break
        if all(abs((j - c).days) >= 2 for c in choisis) or len(sans_course + avec_footing) <= n:
            choisis.append(j)
    for j in sans_course + avec_footing:  # complète si l'espacement était trop strict
        if len(choisis) >= n:
            break
        if j not in choisis:
            choisis.append(j)

    duree = {"base": 50, "dev": 60, "spe": 70, "aff": 40}[phase]
    res = []
    for k, j in enumerate(sorted(choisis)):
        if date_course and 0 <= (date_course - j).days <= 6:
            res.append(fab.recup(j, 30))
        elif k == 1 and phase in ("dev", "spe") and nb_courses <= 4:
            res.append(fab.tempo(j, 3 if phase == "dev" else 4, 8))
        elif j in avec_footing:
            res.append(fab.endurance(j, max(40, duree - 15)))   # double séance : plus court
        else:
            res.append(fab.endurance(j, duree + (10 if k == 0 else 0)))
    return res
