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


def test_forme_graphe_et_reglages(app):
    st, passer = app
    passer(["lien_demo"])
    passer(["accent_objectif"])
    passer(["accent_creer"], obj_distance="Rester en forme", obj_velo=2)
    p = st.session_state.etat["profil"]
    assert p["distance"] == "forme" and p["date_course"] is None
    passer(page="semaine")
    texte = " ".join(str(a) for _, args in st.journal for a in args)
    assert "Ton cycle de 12 semaines" in texte and "<svg" in texte
    passer(page="forme")
    # Réglages : vélo seulement le samedi et le dimanche, renfo coupé
    passer(["primary_plan"], page="reglages", reg_renfo_on=False, reg_jours_velo=["Sam", "Dim"])
    p = st.session_state.etat["profil"]
    assert p["renfo_actif"] is False and p["jours_velo"] == [5, 6]
    ctx = None
    passer(page="semaine")
    ctx = st.session_state.contexte
    assert not [s for s in ctx.plan.seances() if s.sport == "renfo"]
    assert all(s.jour.weekday() in (5, 6) for s in ctx.plan.seances() if s.sport == "velo")


def test_graphe_course_jour_j(app):
    st, passer = app
    passer(["lien_demo"])
    passer(["accent_objectif"])
    passer(["accent_creer"])
    passer(page="semaine")
    texte = " ".join(str(a) for _, args in st.journal for a in args)
    assert "jusqu&#x27;au jour J" in texte or "jusqu'au jour J" in texte


def test_deplacer_depuis_semaine(app):
    st, passer = app
    passer(["lien_demo"])
    passer(["accent_objectif"])
    passer(["accent_creer"])
    passer(page="semaine", decal_semaine=1)
    ctx = st.session_state.contexte
    sem = ctx.plan.semaines[next(i for i, x in enumerate(ctx.plan.semaines) if x.debut > ctx.aujourd_hui)]
    longue = next(x for x in sem.seances if x.genre == "long")
    cle = (longue.origine or longue.ident).replace("-", "_")
    from foulee.engine.seances import JOURS
    lundi = sem.debut
    passer([f"petit_dep_ok_{cle}"], **{f"dep_{cle}_{longue.jour.isoformat()}": f"{JOURS[0][:3]}. {lundi.day}"})
    assert st.session_state.etat["deplacements"][longue.origine] == lundi.isoformat()
    ctx = st.session_state.contexte
    assert any(x.genre == "long" and x.jour == lundi for x in ctx.plan.seances())


def _demarrer(passer):
    passer(["lien_demo"])
    passer(["accent_objectif"])
    passer(["accent_creer"])


def test_annuler_seance_du_jour(app):
    st, passer = app
    _demarrer(passer)
    from datetime import timedelta
    from foulee import coach
    ctx = st.session_state.contexte
    # on se place sur une séance de la semaine prochaine, pas encore faite
    sem = next(x for x in ctx.plan.semaines if x.debut > ctx.aujourd_hui)
    cible = next(x for x in sem.seances if x.genre in ("seuil", "vma", "cotes", "fartlek", "specifique", "long"))
    e = st.session_state.etat
    from foulee.engine import ajustement as AJ
    msg = AJ.annuler(e, ctx.plan, cible, cible.jour, "Fatigue")
    assert "annulée" in msg
    ctx2 = coach.construire(e, st.session_state.donnees, cible.jour)
    sem2 = ctx2.plan.semaine_de(cible.jour)
    assert not any(x.jour == cible.jour and x.genre == cible.genre for x in sem2.seances)
    a = e["annulations"][cible.origine]
    if a["remplace"]:   # reportée à la place d'un footing
        assert any(x.reportee and x.genre == cible.genre for x in sem2.seances)
        assert not any((x.origine or x.ident) == a["remplace"] for x in sem2.seances)
    AJ.retablir(e, cible.origine)
    ctx3 = coach.construire(e, st.session_state.donnees, cible.jour)
    assert any(x.jour == cible.jour and x.genre == cible.genre for x in ctx3.plan.seances())


def test_annuler_depuis_aujourdhui_et_fete(app):
    st, passer = app
    _demarrer(passer)
    ctx = st.session_state.contexte
    passer(page="aujourdhui")
    t = textes(st)
    assert "Cette semaine" in t
    seances = [s for s in ctx.seances_du_jour() if s.ident not in ctx.liens]
    if seances:
        s = seances[0]
        cle = (s.origine or s.ident).replace("-", "_")
        passer([f"petit_annul_{cle}"], **{f"raison_{cle}": "Malade"})
        assert s.origine in st.session_state.etat["annulations"]
        assert "Finalement je la fais" in textes(st)
        passer([f"lien_retablir_{s.origine.replace('-', '_')}"])
        assert s.origine not in st.session_state.etat["annulations"]
    # Objectif de la semaine : fête affichée une seule fois
    ctx = st.session_state.contexte
    faits, prevus = ctx.km_semaine()
    assert prevus > 0
    st.session_state.etat["fetes"] = []
    import foulee.coach as C
    orig = C.Contexte.km_semaine
    C.Contexte.km_semaine = lambda self, sem=None: (40.0, 30.0)
    try:
        passer(page="semaine")
        assert "Objectif de la semaine atteint" in textes(st)
        passer(page="semaine")
        assert "Objectif de la semaine atteint" not in textes(st)
    finally:
        C.Contexte.km_semaine = orig


def test_sortie_fc(app):
    st, passer = app
    _demarrer(passer)
    ctx = st.session_state.contexte
    s, act = next((s, a) for s, a in ((s, ctx.liens.get(s.ident)) for s in ctx.plan.seances()) if a)
    passer(page="sortie", sortie_act=act, sortie_seance=s.ident)
    t = textes(st)
    assert "Ton cœur pendant la sortie" in t and "Z2 Endurance" in t
    assert str(act["id"]) in st.session_state.etat["cardio"]   # analyse gardée pour le coach


def test_historique_et_analyse_groupee(app):
    st, passer = app
    _demarrer(passer)
    passer(page="forme")
    t = textes(st)
    assert "Mes sorties" in t
    boutons = [a[1] for k, a in st.journal if k == "button" and a[1] and a[1].startswith("carte_sortie_")]
    assert len(boutons) == 8
    passer(["petit_analyser_tout"])
    assert len(st.session_state.etat["cardio"]) >= 8
    passer(page="forme")
    passer([boutons[0]])
    assert st.session_state.page == "sortie" and "Ton cœur pendant la sortie" in textes(st)
    passer(["lien_retour_sortie"])
    assert st.session_state.page == "forme"


def test_apercu_seance(app):
    st, passer = app
    _demarrer(passer)
    passer(page="semaine", decal_semaine=1)
    boutons = [a[1] for k, a in st.journal if k == "button" and a[1] and a[1].startswith("petit_apercu_")]
    assert boutons
    passer([boutons[0]])
    assert st.session_state.page == "apercu"
    t = textes(st)
    assert "Aperçu de ta séance" in t and "FC cible" in t and "Pourquoi cette séance" in t
