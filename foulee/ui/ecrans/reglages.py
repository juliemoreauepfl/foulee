"""Réglages : Garmin, données, sorties à la main, couleur, export, remise à zéro."""
from __future__ import annotations

import json
from datetime import time

import streamlit as st

from ... import coach
from ...data.store import StockageLocal
from ...engine.seances import parse_chrono
from .. import etat as E
from .. import theme as T
from ..commun import entete, html, titre
from .bienvenue import _importer


def afficher():
    e = E.etat()
    entete()
    if st.button("‹ Aujourd'hui", key="lien_retour_reglages"):
        E.aller("aujourdhui")
    titre("Réglages", "", 36)

    # --- Données
    st.subheader("Mes données")
    mode = e.get("mode", "garmin")
    stock = E.stockage()
    d = E.donnees()
    maj = d.maj or "jamais"
    source = {"demo": "Démo (données inventées)", "fichiers": "Fichiers importés", "polar": "Polar Flow"}.get(mode, "Garmin Connect")
    html(f'<div class="f-carte"><div class="f-ligne"><span>Source</span><b>{T.esc(source)}</b></div>'
         f'<div class="f-ligne" style="margin-top:6px"><span>Dernière mise à jour</span><span class="f-sous">{T.esc(maj)}</span></div>'
         f'<div class="f-ligne" style="margin-top:6px"><span>Sauvegarde</span><span class="f-sous">{T.esc(stock.nom)}</span></div></div>')
    if mode == "demo":
        if st.button("Quitter la démo et brancher Garmin", key="primary_quitter_demo", type="primary"):
            sauvegarde = {k: e.get(k) for k in ("prenom", "renfo", "accent")}
            nouvel = coach.etat_initial()
            nouvel.update({k: v for k, v in sauvegarde.items() if v})
            nouvel["mode"] = "garmin"
            st.session_state.etat = nouvel
            E.sauver()
            for k in ("donnees", "contexte", "ob_etape", "jeton_polar"):
                st.session_state.pop(k, None)
            E.aller("bienvenue", ob_etape=1)
    else:
        nom = E.NOMS_MARQUES[E.marque()]
        if E.connecte() and st.button(f"Mettre à jour depuis {nom}", key="maj_garmin", type="primary"):
            try:
                with st.spinner("Je récupère tes données…"):
                    E.mettre_a_jour_garmin()
                E.invalider()
                st.success("À jour !")
            except Exception as err:
                st.error(str(err))
        if E.marque() == "polar":
            html('<p class="f-sous" style="margin:0">Polar ne garde que 30 jours : ouvre l\'app au moins une fois '
                 'par mois pour que ton historique s\'accumule ici.</p>')
            if st.button("Reconnecter mon compte Polar", key="petit_reco_polar"):
                for k in ("polar_url", "jeton_polar"):
                    st.session_state.pop(k, None)
                stock.effacer("polar_jeton")
                E.aller("bienvenue", ob_etape=1)
        elif not E.secrets().get("GARMIN_API_KEY"):
            st.text_input("Clé Garmin personnelle", type="password", key="cle_saisie",
                          help="Garmin Connect (web) › Paramètres › Personal API Token.")
            if isinstance(stock, StockageLocal) and st.session_state.get("cle_saisie"):
                if st.button("Retenir la clé sur cet ordinateur", key="petit_retenir"):
                    e["garmin_cle_locale"] = st.session_state.cle_saisie
                    E.sauver()
                    st.toast("Clé enregistrée localement")

    with st.expander("Ajouter une sortie faite sans la montre"):
        with st.form("sortie_manuelle", clear_on_submit=True):
            j = st.date_input("Date", value=E.aujourd_hui(), format="DD/MM/YYYY")
            km = st.number_input("Distance (km)", min_value=0.5, max_value=100.0, value=5.0, step=0.5)
            duree = st.text_input("Durée", placeholder="35:00")
            ok = st.form_submit_button("Ajouter")
        if ok:
            s = parse_chrono(duree)
            if not s:
                st.error("Durée illisible : écris par exemple 35:00 ou 1:05:00.")
            else:
                e.setdefault("sorties_manuelles", []).append(
                    {"id": f"manuel-{j.isoformat()}-{len(e.get('sorties_manuelles', []))}", "date": j.isoformat(),
                     "debut": f"{j.isoformat()}T12:00:00", "nom": "Course (saisie)", "distance_km": km,
                     "duree_s": s, "fc_moy": None, "fc_max": None, "denivele": 0})
                E.sauver()
                st.session_state.pop("donnees", None)
                E.invalider()
                st.success("Sortie ajoutée.")
    with st.expander("Importer des fichiers .FIT / .GPX"):
        fichiers = st.file_uploader("Fichiers", type=["fit", "gpx", "zip"], accept_multiple_files=True,
                                    label_visibility="collapsed")
        if fichiers and st.button("Importer", key="importer_reglages", type="primary"):
            n = _importer(e, fichiers)
            E.sauver()
            st.success(f"{n} sortie(s) importée(s).")

    # --- Plan
    st.subheader("Mon plan")
    pr = e["profil"]
    renfo_on = st.toggle("Inclure le renfo au plan", value=bool(pr.get("renfo_actif", True)), key="reg_renfo_on")
    velo_on = st.toggle("Inclure le vélo / home trainer au plan", value=bool(pr.get("velo_actif", True)),
                        key="reg_velo_on")
    jours_lib = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    jours_sel = pr.get("jours_velo") or list(range(7))
    choix_jours = jours_sel
    if velo_on:
        sel = st.pills("Jours où je peux faire du vélo", jours_lib, selection_mode="multi",
                       default=[jours_lib[j] for j in jours_sel], key="reg_jours_velo")
        choix_jours = sorted(jours_lib.index(j) for j in (sel or []))
        if not pr.get("velo_semaine"):
            html('<p class="f-sous" style="margin:0">Choisis aussi combien de séances vélo par semaine dans <b>Objectif</b>.</p>')
        if velo_on and not choix_jours:
            st.caption("Aucun jour choisi : pas de vélo dans le plan.")
    if st.button("Appliquer à mon plan", key="primary_plan", type="primary"):
        pr["renfo_actif"], pr["velo_actif"] = bool(renfo_on), bool(velo_on)
        pr["jours_velo"] = choix_jours
        E.sauver()
        E.invalider()
        st.toast("Plan mis à jour")
        st.rerun()

    # --- Profil
    st.subheader("Moi")
    prenom = st.text_input("Prénom", value=e.get("prenom", ""))
    sexe = st.segmented_control("Formule de charge (TRIMP)", ["Femme", "Homme", "Neutre"],
                                default={"femme": "Femme", "homme": "Homme"}.get(e["profil"].get("sexe", ""), "Neutre"),
                                key="sexe", help="Les coefficients publiés du TRIMP diffèrent selon le sexe.")
    couleur = st.segmented_control("Couleur principale", ["Orange", "Citron", "Soleil", "Lilas"],
                                   default={"#C8F169": "Citron", "#FFC93C": "Soleil", "#B9A6FF": "Lilas"}.get(e.get("accent"), "Orange"),
                                   key="couleur")
    couleurs = {"Orange": "#FF6B2C", "Citron": "#C8F169", "Soleil": "#FFC93C", "Lilas": "#B9A6FF"}
    ftp = st.number_input("FTP vélo (watts, 0 = inconnue)", min_value=0, max_value=600, step=5,
                          value=int(e["profil"].get("ftp") or 0), key="reg_ftp",
                          help="Après un bon échauffement : 20 min le plus fort possible mais régulier. FTP ≈ 95 % de la puissance moyenne.")
    if st.button("Enregistrer", key="primary_profil", type="primary"):
        e["prenom"] = prenom.strip()
        e["profil"]["ftp"] = int(ftp) if ftp else None
        e["profil"]["sexe"] = {"Femme": "femme", "Homme": "homme"}.get(sexe or "", "")
        e["accent"] = couleurs.get(couleur or "Orange")
        E.sauver()
        E.invalider()
        st.rerun()

    # --- Export / remise à zéro
    st.subheader("Mes données à moi")
    st.download_button("Exporter tout (JSON)", data=json.dumps(e, ensure_ascii=False, indent=1, default=str),
                       file_name="foulee-export.json", mime="application/json", key="export")
    with st.expander("Tout effacer et recommencer"):
        st.warning("Efface ton profil, ton plan, tes bilans et tes préférences de renfo. Irréversible.")
        if st.button("Oui, tout effacer", key="effacer"):
            st.session_state.etat = coach.etat_initial()
            E.sauver()
            for cle in ("cache_garmin", "cache_polar", "polar_jeton", "polar_etat"):
                try:
                    stock.effacer(cle)
                except Exception:
                    pass
            for k in list(st.session_state.keys()):
                if k not in ("stockage", "etat"):
                    st.session_state.pop(k, None)
            E.aller("bienvenue", ob_etape=1)
