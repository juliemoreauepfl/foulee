"""Objectif : distance, date, chrono, nombre de sorties et de séances de renfo."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from ... import coach
from ...engine import vdot as V
from ...engine.seances import fmt_allure, fmt_duree, parse_chrono
from .. import etat as E
from .. import theme as T
from ..commun import entete, html, nav, titre

CODES = {"5 km": "5k", "10 km": "10k", "Semi": "semi", "Marathon": "marathon", "Rester en forme": "forme"}


def afficher():
    e = E.etat()
    p = e["profil"]
    auj = E.aujourd_hui()
    premiere = not e.get("onboarde")
    entete()
    if not premiere:
        nav("objectif")
    titre("C'est quoi<br>le rêve ?", "", 40)

    inverse = {v: k for k, v in CODES.items()}
    dist_lib = st.segmented_control("Distance", list(CODES), default=inverse.get(p.get("distance", "semi"), "Semi"),
                                    key="obj_distance")
    distance = CODES.get(dist_lib or "Semi", "semi")

    forme = distance == "forme"
    date_course, objectif_s = None, None
    if forme:
        html('<div class="f-bleu">Pas de course en vue : on entretient et on progresse en douceur, '
             'par cycles de 4 semaines (3 variées + 1 plus légère) qui se renouvellent tout seuls.</div>')
    if not forme:
        c1, c2 = st.columns(2)
        with c1:
            date_defaut = date.fromisoformat(p["date_course"]) if p.get("date_course") else auj + timedelta(weeks=16)
            date_course = st.date_input("Date de la course", value=max(date_defaut, auj + timedelta(days=14)),
                                        min_value=auj + timedelta(days=14), max_value=auj + timedelta(weeks=52),
                                        format="DD/MM/YYYY", key="obj_date")
        with c2:
            defaut_txt = fmt_duree(p["objectif_s"]) if p.get("objectif_s") else ""
            chrono_txt = st.text_input("Chrono visé (facultatif)", value=defaut_txt, placeholder="1:45:00",
                                       key="obj_chrono")
        objectif_s = parse_chrono(chrono_txt)
        if objectif_s and distance in ("semi", "marathon") and objectif_s < 30 * 60:
            objectif_s *= 60  # « 1:45 » voulait dire 1 h 45
        if chrono_txt and not objectif_s:
            st.caption("Format attendu : 1:45:00 ou 45:30.")

    courses = st.segmented_control("Course à pied par semaine", [2, 3, 4, 5, 6, 7],
                                   default=int(p.get("courses_semaine", 4)), key="obj_courses",
                                   format_func=lambda n: f"{n}×")
    renfo = st.segmented_control("Renfo par semaine (~20 min)", [0, 1, 2, 3],
                                 default=int(p.get("renfo_semaine", 2)), key="obj_renfo",
                                 format_func=lambda n: "Aucun" if n == 0 else f"{n}×")

    velo = st.segmented_control("Vélo / home trainer par semaine (en plus)", [0, 1, 2, 3],
                                default=int(p.get("velo_semaine", 0) or 0), key="obj_velo",
                                format_func=lambda n: "Aucun" if n == 0 else f"{n}×")
    ftp = p.get("ftp")
    if velo:
        ftp = st.number_input("Ta FTP en watts (facultatif)", min_value=0, max_value=600, step=5,
                              value=int(ftp or 0), key="obj_ftp",
                              help="Puissance tenable environ 1 h. Inconnue ? Laisse 0 : les cibles restent en % de FTP.") or None

    d = E.donnees()
    port = coach.portrait(d, e.get("mois_exclus", []), auj)
    vd = port.vdot or 40.0
    if forme:
        verdict = (f"Repère : je te prédis {fmt_duree(V.temps_predit(vd, 10000))} sur 10 km aujourd'hui. "
                   "On garde le cap, sans pression.")
    else:
        semaines = max(1, (date_course - auj).days // 7)
        verdict, _ = V.faisabilite(vd, distance, objectif_s, semaines)
    a = V.allures(vd)
    html(f'''<div class="f-sombre">
      <div class="f-ligne"><span class="f-sous">Ton niveau, d'après tes derniers mois</span>
      <span class="f-titre" style="font-size:24px;color:{E.accent()}">VDOT {vd:.0f}</span></div>
      <div class="f-grille3" style="margin-top:10px">
        <div><div class="f-sous">Footing</div><div class="f-chiffre">{fmt_allure(a["E"][0])}</div></div>
        <div><div class="f-sous">Seuil</div><div class="f-chiffre">{fmt_allure(sum(a["T"]) / 2)}</div></div>
        <div><div class="f-sous">Fractionné</div><div class="f-chiffre">{fmt_allure(sum(a["I"]) / 2)}</div></div>
      </div><p class="f-sous" style="margin:10px 0 0;line-height:1.4">{T.esc(verdict)}</p></div>''')

    libelle = "Créer mon plan" if premiere or not e.get("plan_debut") else "Mettre à jour mon plan"
    if st.button(libelle, key="accent_creer"):
        p.update(distance=distance, date_course=date_course.isoformat() if date_course else None, objectif_s=objectif_s,
                 courses_semaine=int(courses or 4), renfo_semaine=int(renfo if renfo is not None else 2),
                 velo_semaine=int(velo or 0), ftp=int(ftp) if ftp else None)
        coach.demarrer_plan(e, d, auj)
        E.sauver()
        E.invalider()
        st.toast("Plan prêt !")
        E.aller("aujourdhui")
    if not premiere:
        html('<p class="f-sous" style="margin:0">Mettre à jour repart de cette semaine, en gardant tes bilans.</p>')
