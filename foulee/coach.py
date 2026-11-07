"""Assemble tout : données + profil + bilans → plan du jour et analyses.
Aucune dépendance à Streamlit : testable seul."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .data import demo
from .data.donnees import Donnees, courses, filtrer_mois
from .engine import ajustement as AJ
from .engine import charge as C
from .engine import vdot as V
from .engine import vfc as VFC
from .engine.plan import Plan, Profil, generer_plan, lundi


def etat_initial() -> dict:
    return {
        "version": 1,
        "onboarde": False,
        "profil": {"distance": "semi", "date_course": None, "objectif_s": None,
                   "courses_semaine": 4, "renfo_semaine": 2, "sexe": "", "velo_semaine": 0, "ftp": None},
        "mois_exclus": [],
        "plan_debut": None,
        "vdot_depart": None,
        "facteurs": {"allure": 1.0, "volume": 1.0},
        "ajustements": {},
        "notes": [],
        "regles": [],
        "bilans": {},
        "renfo": {"favoris": [], "bannis": [], "materiel": "rien"},
        "renfo_faits": {},
        "douleurs_recentes": {},
    }


def profil_depuis(etat: dict) -> Profil:
    p = etat["profil"]
    return Profil(
        distance=p.get("distance", "semi"),
        date_course=date.fromisoformat(p["date_course"]) if p.get("date_course") else None,
        objectif_s=p.get("objectif_s"),
        courses_semaine=int(p.get("courses_semaine", 4)),
        renfo_semaine=int(p.get("renfo_semaine", 2)),
        sexe=p.get("sexe", ""),
        velo_semaine=int(p.get("velo_semaine", 0) or 0),
        ftp=int(p["ftp"]) if p.get("ftp") else None,
    )


@dataclass
class Portrait:
    volume_hebdo: float
    plus_longue: float
    vdot: Optional[float]
    sorties_semaine: float
    zone_vfc: tuple
    nb_sorties: int
    nb_nuits_vfc: int
    nb_nuits_sommeil: int
    allures: dict = field(default_factory=dict)


def portrait(d: Donnees, mois_exclus: list[str], aujourd_hui: date) -> Portrait:
    acts = courses(filtrer_mois(d.activites, mois_exclus))
    vd = V.vdot_depuis_historique(acts, aujourd_hui, fc_repos=d.fc_repos()) if acts is not None and not acts.empty else None
    return Portrait(
        volume_hebdo=round(C.volume_hebdo(acts, aujourd_hui, 6), 1),
        plus_longue=round(C.plus_longue(acts, aujourd_hui), 1),
        vdot=vd,
        sorties_semaine=round(C.sorties_par_semaine(acts, aujourd_hui), 1),
        zone_vfc=VFC.zone_habituelle(d.vfc, aujourd_hui),
        nb_sorties=0 if acts is None else len(acts),
        nb_nuits_vfc=0 if d.vfc is None else len(d.vfc),
        nb_nuits_sommeil=0 if d.sommeil is None else len(d.sommeil),
        allures=V.allures(vd) if vd else {},
    )


@dataclass
class Contexte:
    aujourd_hui: date
    donnees: Donnees
    activites: pd.DataFrame
    plan: Plan
    profil: Profil
    meteo: VFC.Meteo
    liens: dict
    libres: list
    charge: pd.DataFrame
    vdot: float
    en_attente: list
    messages: list

    def seances_du_jour(self):
        return self.plan.du_jour(self.aujourd_hui)

    def semaine(self):
        return self.plan.semaine_de(self.aujourd_hui)


def construire(etat: dict, d: Donnees, aujourd_hui: date) -> Contexte:
    profil = profil_depuis(etat)
    acts_hist = courses(filtrer_mois(d.activites, etat.get("mois_exclus", [])))
    profil.fc_max = C.fc_max_estimee(d.activites)
    vd = etat.get("vdot_depart") or V.vdot_depuis_historique(acts_hist, aujourd_hui, fc_repos=d.fc_repos()) or 40.0
    debut = date.fromisoformat(etat["plan_debut"]) if etat.get("plan_debut") else aujourd_hui
    port = portrait(d, etat.get("mois_exclus", []), debut)
    f = etat.get("facteurs", {})
    plan = generer_plan(profil, debut, vd, port.volume_hebdo, port.plus_longue,
                        facteur_allure=f.get("allure", 1.0), facteur_volume=f.get("volume", 1.0))

    activites = d.activites
    if d.source == "demo":
        # En démo, on « suit » le plan pour que l'app ait de la vie
        suivi = demo.simuler_suivi(plan.seances(), aujourd_hui)
        if not suivi.empty:
            avant = activites[activites["date"] < debut] if not activites.empty else activites
            activites = pd.concat([avant, suivi], ignore_index=True)

    AJ.appliquer_ajustements(plan, etat.get("ajustements", {}))
    seances_plan = plan.seances()
    a_apparier = activites[activites["date"] >= debut] if not activites.empty else activites
    liens, libres = AJ.apparier(seances_plan, a_apparier)
    met = VFC.meteo(d.vfc, aujourd_hui)
    messages = AJ.regles_du_jour(etat, plan, met, aujourd_hui, liens)
    if messages:
        plan = generer_plan(profil, debut, vd, port.volume_hebdo, port.plus_longue,
                            facteur_allure=etat["facteurs"].get("allure", 1.0),
                            facteur_volume=etat["facteurs"].get("volume", 1.0))
        AJ.appliquer_ajustements(plan, etat.get("ajustements", {}))
        liens, libres = AJ.apparier(plan.seances(), a_apparier)

    fc_max = C.fc_max_estimee(activites) or 190.0
    serie = C.serie_charge(activites, d.fc_repos(), fc_max, profil.sexe,
                           aujourd_hui - timedelta(days=120), aujourd_hui)
    attente = AJ.bilans_en_attente(etat, liens, libres, plan, aujourd_hui)
    return Contexte(aujourd_hui, d, activites, plan, profil, met, liens, libres, serie, vd, attente, messages)


def demarrer_plan(etat: dict, d: Donnees, aujourd_hui: date) -> None:
    """Fige le point de départ du plan (appelé en validant l'objectif)."""
    acts = courses(filtrer_mois(d.activites, etat.get("mois_exclus", [])))
    etat["vdot_depart"] = V.vdot_depuis_historique(acts, aujourd_hui, fc_repos=d.fc_repos()) or 40.0
    etat["plan_debut"] = (aujourd_hui - timedelta(days=10) if d.source == "demo" else aujourd_hui).isoformat()
    etat["facteurs"] = {"allure": 1.0, "volume": 1.0}
    etat["ajustements"] = {}
    etat["regles"] = []
    etat["onboarde"] = True
