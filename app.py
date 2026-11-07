"""Foulée — lance l'app avec :  streamlit run app.py"""
import hmac
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Foulée", page_icon=str(Path(__file__).parent / "assets" / "icone.png"), layout="centered",
                   initial_sidebar_state="collapsed")

from foulee.ui import etat as E  # noqa: E402
from foulee.ui import theme as T  # noqa: E402
from foulee.ui.ecrans import (aujourdhui, bienvenue, bilan, forme, objectif, reglages, sortie,  # noqa: E402
                              renfo, semaine)

st.markdown(T.css(E.accent()), unsafe_allow_html=True)


def porte_d_entree() -> bool:
    """Mot de passe facultatif (secret APP_PASSWORD) si ton app n'est pas privée."""
    mdp = E.secrets().get("APP_PASSWORD")
    if not mdp or st.session_state.get("entree_ok"):
        return True
    st.markdown(T.compact(f'<div style="padding-top:40px">{T.logo(taille=48)}'
                          '<h1 class="f-titre" style="font-size:40px;margin:12px 0 4px">foulée</h1>'
                          '<p class="f-sous">Ton coach de poche. Mot de passe, s\'il te plaît.</p></div>'),
                unsafe_allow_html=True)
    saisie = st.text_input("Mot de passe", type="password", label_visibility="collapsed")
    if saisie:
        if hmac.compare_digest(saisie, str(mdp)):
            st.session_state.entree_ok = True
            st.rerun()
        st.error("Ce n'est pas le bon mot de passe.")
    return False


def retour_polar():
    """Polar renvoie ici avec ?code=… après ton accord : on échange le code contre un jeton."""
    q = st.query_params
    if "code" not in q:
        return
    from foulee.data.polar import PolarErreur, echanger_code
    sec, s = E.secrets(), E.stockage()
    attendu = (s.lire("polar_etat", {}) or {})
    code, etat_recu = q.get("code"), q.get("state")
    st.query_params.clear()
    if not attendu or attendu.get("etat") != etat_recu:
        st.error("Lien de connexion Polar périmé : recommence depuis l'écran d'accueil.")
        return
    try:
        jeton = echanger_code(sec["POLAR_CLIENT_ID"], sec["POLAR_CLIENT_SECRET"], code,
                              sec.get("APP_URL", "http://localhost:8501").rstrip("/") + "/")
    except (PolarErreur, KeyError) as err:
        st.error(str(err))
        return
    s.ecrire("polar_jeton", jeton)
    s.effacer("polar_etat")
    st.session_state.jeton_polar = jeton
    e = E.etat()
    e["mode"] = "polar"
    e["prenom"] = e.get("prenom") or attendu.get("prenom", "")
    E.sauver()
    st.session_state.pop("donnees", None)
    E.invalider()
    st.toast("Compte Polar connecté !")
    E.aller("bienvenue" if not e.get("onboarde") else "reglages", ob_etape=2)


ECRANS = {
    "bienvenue": bienvenue.afficher,
    "aujourdhui": aujourdhui.afficher,
    "semaine": semaine.afficher,
    "forme": forme.afficher,
    "objectif": objectif.afficher,
    "renfo": renfo.seance,
    "exercice": renfo.exercice,
    "biblio": renfo.bibliotheque,
    "bilan": bilan.afficher,
    "reglages": reglages.afficher,
    "sortie": sortie.afficher,
}

if porte_d_entree():
    retour_polar()
    page = E.page_courante()
    if not E.etat().get("onboarde") and page not in ("bienvenue", "objectif"):
        page = "bienvenue"
    ECRANS.get(page, aujourdhui.afficher)()
