"""Aperçu d'une séance à venir : étapes, allures, FC cible, fichier pour la montre."""
from __future__ import annotations

import streamlit as st

from ...engine.seances import fmt_date
from .. import cardio as CAR
from .. import etat as E
from ..commun import bouton_fit, boutons_velo, carte_seance, entete, html, jour_txt, note_coach, titre


def afficher():
    ctx = E.contexte()
    ident = st.session_state.get("apercu_seance")
    s = next((x for x in ctx.plan.seances() if x.ident == ident), None)
    if s is None:
        E.aller("semaine")
    entete(fmt_date(s.jour))
    if st.button("‹ Semaine", key="lien_retour_apercu"):
        E.aller("semaine")
    titre(jour_txt(s.jour, ctx.aujourd_hui), "Aperçu de ta séance", 32)
    carte_seance(s, "Prévue " + jour_txt(s.jour, ctx.aujourd_hui).lower(), None, CAR.cible_txt(s))
    pourquoi = {
        "footing": "Le footing construit le moteur : plus de capillaires, plus de mitochondries, des tendons plus solides. Lent = utile.",
        "long": "La sortie longue apprend à ton corps à durer : endurance, économie de course et mental.",
        "seuil": "Le seuil recule le moment où tu « satures ». C'est la séance reine du semi et du 10 km.",
        "vma": "La VMA élève ton plafond : tout le reste devient plus facile en dessous.",
        "cotes": "Les côtes, c'est du renfo en courant : puissance, foulée et VMA, avec moins de chocs.",
        "fartlek": "Le fartlek joue avec les allures : on apprend à changer de rythme sans se cramer.",
        "specifique": "L'allure course : tu apprends à ton corps exactement ce qu'on lui demandera le jour J.",
        "rappel": "Un petit rappel d'allure pour garder les jambes vives sans fatiguer.",
        "course": "Le jour J ! Pars prudemment, tu accéléreras dans la deuxième moitié.",
        "velo_endurance": "Du cardio sans impact : tes jambes travaillent, tes tendons se reposent.",
        "velo_tempo": "Un effort soutenu sans chocs, qui fait monter ton seuil.",
        "velo_recup": "On fait tourner les jambes pour récupérer plus vite.",
    }.get(s.genre)
    if pourquoi:
        html(f'<div class="f-carte"><h2 class="f-titre" style="font-size:18px">Pourquoi cette séance ?</h2>'
             f'<p class="f-sous" style="margin:6px 0 0;line-height:1.45;font-size:14px">{pourquoi}</p></div>')
    if s.sport == "velo":
        boutons_velo(s, f"apercu_{s.ident}")
    elif s.sport in ("course", "course_cible"):
        bouton_fit(s, f"apercu_{s.ident}")
    if s.sport == "renfo":
        if st.button("Ouvrir le renfo", key="accent_apercu_renfo"):
            E.aller("renfo", renfo_jour=s.jour)
    for n in [n for n in E.etat().get("notes", []) if n["jour"] == s.jour.isoformat()][-2:]:
        note_coach(n["texte"])
