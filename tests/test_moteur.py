from datetime import date, timedelta

import pytest

from foulee import coach
from foulee.data import demo, fitfile
from foulee.data.donnees import donnees_demo
from foulee.engine import ajustement as AJ
from foulee.engine import renfo as R
from foulee.engine import vdot as V
from foulee.engine.plan import Profil, generer_plan
from foulee.engine.seances import parse_chrono

AUJ = date(2026, 11, 7)


def test_vdot_valeurs_de_reference():
    # Tables de Daniels : 5 km en 20:00 ≈ VDOT 49,8 ; 10 km en 50:00 ≈ 40
    assert V.vdot_depuis_course(5000, 20 * 60) == pytest.approx(49.8, abs=0.3)
    assert V.vdot_depuis_course(10000, 50 * 60) == pytest.approx(40.0, abs=0.5)
    # Aller-retour prédiction
    assert V.temps_predit(49.8, 5000) == pytest.approx(1200, abs=5)


def test_allures_ordonnees():
    a = V.allures(44)
    assert a["R"][0] < a["I"][0] < a["T"][0] < a["M"][0] < a["E"][0] < a["E"][1]


def test_parse_chrono():
    assert parse_chrono("1:45:00") == 6300
    assert parse_chrono("45:30") == 2730
    assert parse_chrono("1h45") == 6300


def test_plan_semi():
    p = Profil("semi", AUJ + timedelta(weeks=16), 6300, 5, 2)
    plan = generer_plan(p, AUJ, 44, 28, 18)
    assert len(plan.semaines) == 17
    seances = plan.seances()
    assert seances[-1].genre == "course" and seances[-1].jour == p.date_course
    assert all(s.jour >= AUJ for s in seances)
    vols = [s.km for s in plan.semaines[1:-2]]  # la 1re semaine est partielle
    for a, b in zip(vols, vols[1:]):
        assert b <= a * 1.25 + 3  # pas de bond brutal
    for sem in plan.semaines[1:-2]:
        assert sum(1 for s in sem.seances if s.sport == "renfo") == 2
        assert sum(1 for s in sem.seances if s.sport == "course") == 5
    # Pas de renfo la veille d'une séance dure
    dures = {s.jour for s in seances if s.genre not in ("footing", "renfo")}
    for s in seances:
        if s.sport == "renfo":
            assert s.jour + timedelta(days=1) not in dures


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7])
@pytest.mark.parametrize("dist", ["5k", "10k", "semi", "marathon"])
def test_plan_toutes_configs(n, dist):
    p = Profil(dist, AUJ + timedelta(weeks=10), None, n, 1)
    plan = generer_plan(p, AUJ, 42, 20, 12)
    assert plan.seances()
    for s in plan.seances():
        assert s.minutes >= 0 and s.km >= 0


def test_fit_aller_retour():
    p = Profil("semi", AUJ + timedelta(weeks=12), None, 5, 0)
    plan = generer_plan(p, AUJ, 44, 30, 15)
    seance = next(s for s in plan.seances() if s.genre in ("seuil", "vma"))
    data = fitfile.ecrire_seance(seance)
    assert fitfile.verifier_crc(data)
    msgs = fitfile.lire_messages(data)
    globaux = [g for g, _ in msgs]
    assert globaux[0] == fitfile.FILE_ID and globaux[1] == fitfile.WORKOUT
    steps = [v for g, v in msgs if g == fitfile.WORKOUT_STEP]
    wk = next(v for g, v in msgs if g == fitfile.WORKOUT)
    assert wk[6] == len(steps)
    rep = [s for s in steps if s[1] == fitfile.DUREE_REPETER]
    assert len(rep) == 1 and rep[0][4] == seance.blocs[1].repetitions
    effort = steps[rep[0][2]]
    assert effort[3] == fitfile.CIBLE_VITESSE and effort[5] < effort[6]


def test_renfo_respecte_bannis_et_materiel():
    for choix in (R.RIEN, R.ELASTIQUE, R.KETTLEBELL):
        exos = R.composer_seance(choix, AUJ, bannis=["pont-levis", "planche"])
        assert len(exos) == 5
        assert all(e.materiel in R.materiel_autorise(choix) for e in exos)
        assert all(e.id not in ("pont-levis", "planche") for e in exos)
        assert len({e.id for e in exos}) == 5
    k = R.composer_seance(R.KETTLEBELL, AUJ)
    assert sum(e.materiel == R.KETTLEBELL for e in k) >= 2
    # stable dans la journée
    assert R.composer_seance(R.RIEN, AUJ) == R.composer_seance(R.RIEN, AUJ)


def test_parcours_complet_demo():
    d = donnees_demo(AUJ)
    etat = coach.etat_initial()
    etat["profil"].update(distance="semi", date_course=(AUJ + timedelta(weeks=17)).isoformat(),
                          objectif_s=6300, courses_semaine=5, renfo_semaine=2)
    port = coach.portrait(d, ["2026-09"], AUJ)
    assert 35 < port.vdot < 55 and port.volume_hebdo > 10
    coach.demarrer_plan(etat, d, AUJ)
    ctx = coach.construire(etat, d, AUJ)
    assert ctx.plan.seances()
    assert ctx.meteo.etat in ("soleil", "eclaircies", "nuages", "orage", "voile")
    assert ctx.liens, "les sorties simulées doivent être reliées au plan"
    # Bilan avec douleur → la sortie longue suivante est raccourcie
    s, act = next((s, a) for s, a in [(s, ctx.liens[s.ident]) for s in ctx.plan.seances() if s.ident in ctx.liens])
    bilan = {"cle": str(act["id"]), "jour": AUJ.isoformat(), "type": "course", "genre": s.genre,
             "ressenti": "dur", "douleurs": ["Genou"], "conformite": []}
    titre, texte = AJ.traiter_bilan(etat, ctx.plan, bilan, AUJ)
    assert "genou" in texte.lower()
    ctx2 = coach.construire(etat, d, AUJ)
    longue = next(s for s in ctx2.plan.seances() if s.genre == "long" and s.jour > AUJ)
    assert longue.allegee
    assert "genou" in AJ.douleurs_recentes(etat, AUJ)


def test_conformite():
    p = Profil("10k", AUJ + timedelta(weeks=8), None, 4, 0)
    plan = generer_plan(p, AUJ, 44, 30, 12)
    s = next(x for x in plan.seances() if x.genre in ("seuil", "vma", "fartlek"))
    tours = demo.tours_simules(s, "x")
    res = AJ.conformite(s, tours)
    assert res and all(r["statut"] in ("pile", "un poil lent", "trop lent", "un peu vite") for r in res)


def test_velo_plan_fit_zwo():
    import xml.etree.ElementTree as ET
    from foulee.data.zwo import ecrire_zwo
    p = Profil("semi", AUJ + timedelta(weeks=14), None, 4, 1, "", 2, 220, 186)
    plan = generer_plan(p, AUJ, 44, 28, 15)
    velos = [s for s in plan.seances() if s.sport == "velo"]
    assert velos
    for sem in plan.semaines[1:-1]:
        assert sum(1 for s in sem.seances if s.sport == "velo") == 2
    dures = {s.jour for s in plan.seances() if s.sport == "course" and s.genre not in ("footing",)}
    assert not any(v.jour in dures for v in velos)
    tempo = next(s for s in velos if s.genre == "velo_tempo")
    data = fitfile.ecrire_seance(tempo)
    assert fitfile.verifier_crc(data)
    msgs = fitfile.lire_messages(data)
    assert next(v for g, v in msgs if g == fitfile.WORKOUT)[4] == 2          # sport vélo
    effort = [v for g, v in msgs if g == fitfile.WORKOUT_STEP and v[3] == fitfile.CIBLE_PUISSANCE]
    assert effort and all(0 < v[5] < v[6] <= 150 for v in effort)            # % FTP
    racine = ET.fromstring(ecrire_zwo(tempo))
    assert racine.find("sportType").text == "bike"
    assert racine.find("workout/IntervalsT").get("Repeat") == "3" or racine.find("workout/IntervalsT").get("Repeat") == "4"
    assert "W" in " ".join(b for _, b in __import__("foulee.engine.seances", fromlist=["x"]).resume_etapes(tempo))


def test_douleur_impact_passe_en_velo():
    d = donnees_demo(AUJ)
    etat = coach.etat_initial()
    etat["profil"].update(distance="10k", date_course=(AUJ + timedelta(weeks=10)).isoformat(),
                          courses_semaine=4, renfo_semaine=0, velo_semaine=1, ftp=200)
    coach.demarrer_plan(etat, d, AUJ)
    ctx = coach.construire(etat, d, AUJ)
    bilan = {"cle": "x", "jour": AUJ.isoformat(), "type": "course", "genre": "footing", "ressenti": "correct",
             "douleurs": ["Achille"], "conformite": [], "velo_possible": True}
    AJ.traiter_bilan(etat, ctx.plan, bilan, AUJ)
    ctx2 = coach.construire(etat, d, AUJ)
    remplace = [s for s in ctx2.plan.seances() if s.sport == "velo" and s.allegee]
    assert remplace, "le prochain footing doit passer en vélo"
