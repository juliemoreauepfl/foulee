"""Détail d'une sortie : résumé + FC tout au long de la course, analysée."""
from __future__ import annotations

import streamlit as st

from ...engine.seances import fmt_allure, fmt_date, fmt_duree, fmt_km
from .. import cardio as CAR
from .. import etat as E
from ..commun import entete, extras_html, html, titre


def afficher():
    ctx = E.contexte()
    act = st.session_state.get("sortie_act")
    if not act:
        E.aller("semaine")
    ident = st.session_state.get("sortie_seance")
    seance = next((s for s in ctx.plan.seances() if s.ident == ident), None)
    entete(fmt_date(act["date"]))
    if st.button("‹ Retour", key="lien_retour_sortie"):
        E.aller(st.session_state.get("page_avant_sortie", "semaine"))
    titre(seance.titre.split("·")[0].strip() if seance else act.get("nom", "Sortie"), "", 32)
    velo = act.get("sport") == "velo"
    vit = (f"{act['distance_km'] / (act['duree_s'] / 3600):.0f} km/h" if velo and act.get("duree_s")
           else fmt_allure(act["duree_s"] / act["distance_km"]) if act.get("distance_km") else "–")
    html(f'''<div class="f-sombre"><div class="f-grille3">
        <div><div class="f-sous">Distance</div><div class="f-chiffre">{fmt_km(act["distance_km"])}</div></div>
        <div><div class="f-sous">Durée</div><div class="f-chiffre">{fmt_duree(act["duree_s"])}</div></div>
        <div><div class="f-sous">{"Vitesse" if velo else "Allure"}</div><div class="f-chiffre">{vit}</div></div></div>
        {extras_html(act.get("extras"), sombre=True)}</div>''')
    CAR.carte(CAR.analyse(act, seance))
