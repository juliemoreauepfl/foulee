"""Parcours complet de l'app en mode démo, avec un faux Streamlit."""
import importlib
import runpy
import sys
from datetime import date
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    from tests import faux_streamlit
    st = faux_streamlit.installer()
    for m in [m for m in sys.modules if m.startswith("foulee.ui")]:
        del sys.modules[m]
    import foulee.ui.etat as E
    monkeypatch.setattr(E, "RACINE", tmp_path)

    def passer(clics=(), max_reruns=8, **etat_session):
        st.session_state.update(etat_session)
        st.clics = set(clics)
        for _ in range(max_reruns):
            st.journal = []
            try:
                runpy.run_path(str(RACINE / "app.py"), run_name="__main__")
                return st
            except faux_streamlit.Rerun:
                continue
        return st
    return st, passer


def textes(st):
    return " ".join(str(a) for _, args in st.journal for a in args)


def test_parcours_demo(app):
    st, passer = app
    passer()
    assert st.session_state.page == "bienvenue"
    passer(["lien_demo"])                      # démo → import → portrait
    assert st.session_state.get("ob_etape") == 3
    assert "compris de toi" in textes(st)
    passer(["accent_objectif"])
    assert st.session_state.page == "objectif"
    passer(["accent_creer"])
    assert st.session_state.page == "aujourdhui"
    t = textes(st)
    assert "Météo intérieure" in t

    for page in ("semaine", "forme", "objectif", "renfo", "biblio", "reglages"):
        passer(page=page)
        assert st.session_state.page == page, page

    # Bilan de la sortie du jour (la démo « suit » le plan)
    passer(page="aujourdhui")
    if "accent_bilan_0" in [a[1] for k, a in st.journal if k == "button"]:
        passer(["accent_bilan_0"])
        assert st.session_state.page == "bilan"
        passer(["accent_envoyer"], bilan_ressenti="Dur", bilan_douleurs=["Genou"])
        assert st.session_state.get("bilan_reponse")
        passer(["accent_fin_bilan"])
        assert st.session_state.page == "aujourdhui"

    # Séance de renfo complète avec kettlebell
    passer(page="renfo", renfo_jour=date.today(), materiel="Kettlebell")
    passer(["accent_go"])
    assert st.session_state.page == "exercice"
    for _ in range(5):
        for _ in range(3):
            passer(["accent_serie"])
        passer(["accent_suivant"])
    passer(["accent_fin_renfo"], ressenti_renfo="Correct")
    assert st.session_state.page == "aujourdhui"
    assert st.session_state.etat["renfo_faits"]

    # Favori et bannissement depuis la bibliothèque
    passer(["petit_ban_biblio_planche", "petit_fav_biblio_crabe"], page="biblio")
    pr = st.session_state.etat["renfo"]
    assert "planche" in pr["bannis"] and "crabe" in pr["favoris"]

    # Semaine suivante, puis précédente
    passer(["petit_suiv"], page="semaine")
    passer(["petit_prec"], page="semaine")


def test_parcours_polar(app, monkeypatch):
    st, passer = app
    from foulee.data import polar as P
    from tests.test_polar import FauxPolar
    st.secrets = {"POLAR_CLIENT_ID": "cid", "POLAR_CLIENT_SECRET": "sec"}
    monkeypatch.setattr(P, "echanger_code", lambda *a: {"access_token": "tok", "user_id": "42"})
    monkeypatch.setattr(P.ClientPolar, "get", FauxPolar.get)

    passer(choix_montre="Polar")
    assert "Connecter mon compte Polar" in [a[0] for k, a in st.journal if k == "button"]
    etat_oauth = st.session_state.stockage.lire("polar_etat")["etat"]
    # Retour de Polar avec le code
    st.query_params.update({"code": "abc", "state": etat_oauth})
    passer()
    assert st.session_state.etat["mode"] == "polar"
    assert st.session_state.get("ob_etape") == 3          # import fait, portrait affiché
    assert len(st.session_state.donnees.activites) == 2   # course + vélo
    passer(["accent_objectif"])
    passer(["accent_creer"])
    assert st.session_state.page == "aujourdhui"
    # Pas de bouton de fichier .fit pour Polar
    passer(page="aujourdhui")
    assert not [a for k, a in st.journal if k == "download"]


def test_parcours_velo(app):
    st, passer = app
    passer(["lien_demo"])
    passer(["accent_objectif"])
    passer(["accent_creer"], obj_velo=2, obj_ftp=210)
    assert st.session_state.etat["profil"]["velo_semaine"] == 2
    assert st.session_state.etat["profil"]["ftp"] == 210
    vus = set()
    for page in ("semaine", "aujourdhui", "forme", "reglages"):
        passer(page=page)
        texte = " ".join(str(a) for _, args in st.journal for a in args)
        if "Vélo" in texte or "vélo" in texte:
            vus.add(page)
    assert "semaine" in vus
    # Sur 3 semaines, au moins une séance vélo propose les exports .zwo
    zwo = False
    for decal in range(3):
        st.session_state.decal_semaine = decal
        ctx = st.session_state.contexte
        for s in ctx.plan.seances():
            if s.sport == "velo":
                zwo = True
    assert zwo
