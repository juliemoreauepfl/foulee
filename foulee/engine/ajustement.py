"""Le coach : relie les sorties au plan, lit les bilans et ajuste la suite.

Toutes les décisions sont des règles simples et explicites, chacune
expliquée par une note visible dans l'app."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .plan import Plan
from .seances import CONTINU, EFFORT, Bloc, Etape, Seance, fmt_allure, fmt_duree
from .vfc import NUAGES, ORAGE, Meteo

RESSENTIS = [("balade", "Balade"), ("facile", "Facile"), ("correct", "Correct"), ("dur", "Dur"),
             ("lumiere", "J'ai vu la lumière")]
NIVEAU = {k: i + 1 for i, (k, _) in enumerate(RESSENTIS)}
ATTENDU = {"footing": 2, "long": 3, "cotes": 4, "fartlek": 3, "vma": 4, "seuil": 4, "specifique": 4,
           "rappel": 3, "course": 5, "renfo": 3, "velo_endurance": 2, "velo_tempo": 4, "velo_recup": 1}
ZONES = ["Pied", "Achille", "Mollet", "Genou", "Hanche", "Dos"]
QUALITE = {"cotes", "fartlek", "vma", "seuil", "specifique", "rappel"}


# ------------------------------------------------------------ appariement
def apparier(seances: list[Seance], activites) -> tuple[dict, list]:
    """Associe chaque sortie à une séance prévue : même jour, sinon ±1 jour."""
    lien: dict[str, dict] = {}
    libres = []
    if activites is None or len(activites) == 0:
        return lien, libres
    def sport_seance(s):
        return "velo" if s.sport == "velo" else ("course" if s.sport in ("course", "course_cible") else None)
    prevues = [s for s in seances if sport_seance(s)]
    for act in activites.sort_values("debut").to_dict("records"):
        sport = act.get("sport") or "course"
        if sport not in ("course", "velo"):
            sport = "course"
        candidats = [s for s in prevues if s.ident not in lien and sport_seance(s) == sport
                     and abs((s.jour - act["date"]).days) <= 1]
        candidats.sort(key=lambda s: abs((s.jour - act["date"]).days))
        if candidats:
            lien[candidats[0].ident] = act
        else:
            libres.append(act)
    return lien, libres


# ------------------------------------------------------------ modifications du plan
def appliquer_ajustements(plan: Plan, ajustements: dict) -> Plan:
    if not ajustements:
        return plan
    lo, hi = plan.allures["E"]
    for sem in plan.semaines:
        nouvelles = []
        for s in sem.seances:
            aj = ajustements.get(s.jour.isoformat())
            if aj and s.sport == "course":
                if aj["type"] == "repos":
                    continue
                if aj["type"] == "footing":
                    m = int(aj.get("minutes", 30))
                    s = Seance(s.jour, "course", "footing", f"Footing · {fmt_duree(m * 60, court=True)}",
                               [Bloc([Etape(CONTINU, duree_s=m * 60, allure_min=lo, allure_max=hi)])],
                               round(m * 60 / ((lo + hi) / 2), 1), m, aj.get("note", ""), allegee=True)
                elif aj["type"] == "velo":
                    from .velo import FabriqueVelo
                    s = FabriqueVelo(getattr(plan, "ftp", None), getattr(plan, "fc_max", None)).remplacer_footing(s)
                    s.note = aj.get("note", s.note)
                elif aj["type"] == "raccourcir":
                    f = float(aj.get("facteur", 0.8))
                    for b in s.blocs:
                        for e in b.etapes:
                            if e.type == CONTINU and e.duree_s:
                                e.duree_s = int(5 * round(e.duree_s * f / 300) * 60)
                    s.minutes = int(s.minutes * f)
                    s.km = round(s.km * f, 1)
                    s.titre = s.titre.split("·")[0].strip() + f" · {fmt_duree(s.minutes * 60, court=True)}"
                    s.note, s.allegee = aj.get("note", s.note), True
            nouvelles.append(s)
        sem.seances = nouvelles
        sem.km = round(sum(x.km for x in nouvelles), 1)
    return plan


def _noter(etat: dict, jour: date, texte: str, cle: str):
    notes = etat.setdefault("notes", [])
    if any(n.get("cle") == cle for n in notes):
        return
    notes.append({"jour": jour.isoformat(), "texte": texte, "cle": cle})


def _regle_deja(etat: dict, cle: str) -> bool:
    deja = etat.setdefault("regles", [])
    if cle in deja:
        return True
    deja.append(cle)
    return False


# ------------------------------------------------------------ règles du jour
def regles_du_jour(etat: dict, plan: Plan, meteo: Meteo, aujourd_hui: date, liens: dict) -> list[str]:
    """Règles vérifiées à chaque ouverture. Retourne les messages ajoutés."""
    messages = []
    aj = etat.setdefault("ajustements", {})
    du_jour = [s for s in plan.du_jour(aujourd_hui) if s.sport == "course" and s.genre in QUALITE | {"long"}]
    cle = f"vfc-{aujourd_hui.isoformat()}"
    if du_jour and meteo.lever_le_pied and aujourd_hui.isoformat() not in aj and not _regle_deja(etat, cle):
        s = du_jour[0]
        if meteo.etat == ORAGE:
            aj[aujourd_hui.isoformat()] = {"type": "footing", "minutes": 25,
                                          "note": "Orage intérieur : simple balade de 25 min, ou repos si tu préfères."}
            txt = f"{s.titre.split('·')[0].strip()} remplacé par une balade : ta VFC est très basse depuis plusieurs nuits."
        else:
            m = 35 if s.genre != "long" else max(40, int(s.minutes * 0.7))
            aj[aujourd_hui.isoformat()] = {"type": "footing", "minutes": m,
                                          "note": "VFC sous ta zone : footing tranquille au lieu de la séance prévue."}
            txt = f"{s.titre.split('·')[0].strip()} remplacé par un footing de {m} min : ta VFC est sous ta zone."
        _noter(etat, aujourd_hui, txt, cle)
        messages.append(txt)

    # Séances manquées : 3 sorties prévues non faites sur 14 jours → on ralentit la progression
    passees = [s for s in plan.seances()
               if s.sport == "course" and aujourd_hui - timedelta(days=14) <= s.jour < aujourd_hui]
    manquees = [s for s in passees if s.ident not in liens]
    semaine = aujourd_hui.isocalendar()
    cle = f"manquees-{semaine.year}-{semaine.week}"
    if len(passees) >= 4 and len(manquees) >= 3 and not _regle_deja(etat, cle):
        f = etat.setdefault("facteurs", {"allure": 1.0, "volume": 1.0})
        f["volume"] = round(max(0.7, f.get("volume", 1.0) * 0.92), 3)
        txt = (f"{len(manquees)} séances sautées ces deux dernières semaines : je baisse un peu le volume "
               "pour repartir sur de bonnes bases. On ne rattrape jamais une séance ratée.")
        _noter(etat, aujourd_hui, txt, cle)
        messages.append(txt)
    return messages


# ------------------------------------------------------------ conformité aux allures
def conformite(seance: Seance, tours: list[dict]) -> list[dict]:
    """Compare chaque bloc d'effort prévu aux tours de la montre."""
    efforts = []
    for b in seance.blocs:
        for _ in range(b.repetitions):
            for e in b.etapes:
                if e.type == EFFORT and e.allure_min:
                    efforts.append(e)
    if not efforts or not tours:
        return []
    etapes_detaillees = [e for b in seance.blocs for _ in range(b.repetitions) for e in b.etapes]
    if len(tours) == len(etapes_detaillees):
        paires = [(e, t) for e, t in zip(etapes_detaillees, tours) if e.type == EFFORT and e.allure_min]
    else:
        # Repli : les tours les plus rapides sont les efforts, dans l'ordre
        rapides = sorted(range(len(tours)), key=lambda i: tours[i].get("allure") or 9999)[:len(efforts)]
        paires = list(zip(efforts, [tours[i] for i in sorted(rapides)]))
    res = []
    for k, (e, t) in enumerate(paires, 1):
        prevu = (e.allure_min + e.allure_max) / 2
        reel = t.get("allure")
        if not reel:
            continue
        ecart = (reel - prevu) / prevu
        if ecart > 0.05:
            statut, ton = "trop lent", "lent"
        elif ecart > 0.02:
            statut, ton = "un poil lent", "lent"
        elif ecart < -0.04:
            statut, ton = "un peu vite", "vite"
        else:
            statut, ton = "pile", "ok"
        res.append({"bloc": f"Bloc {k}", "prevu": fmt_allure(prevu), "reel": fmt_allure(reel),
                    "statut": statut, "ton": ton, "ecart": ecart})
    return res


# ------------------------------------------------------------ bilan
def traiter_bilan(etat: dict, plan: Plan, bilan: dict, aujourd_hui: date) -> tuple[str, str]:
    """Enregistre le bilan et applique les règles. Retourne (titre, texte) de la réponse."""
    etat.setdefault("bilans", {})[bilan["cle"]] = bilan
    genre = bilan.get("genre", "footing")
    ecart = NIVEAU.get(bilan["ressenti"], 3) - ATTENDU.get(genre, 3)
    douleurs = bilan.get("douleurs", [])
    f = etat.setdefault("facteurs", {"allure": 1.0, "volume": 1.0})
    aj = etat.setdefault("ajustements", {})
    a_venir = [s for s in plan.seances() if s.jour > aujourd_hui and s.sport == "course"]
    phrases = []

    # 1. Douleur
    if douleurs:
        recents = [b for b in etat["bilans"].values()
                   if b is not bilan and date.fromisoformat(b["jour"]) >= aujourd_hui - timedelta(days=14)]
        repetees = [z for z in douleurs if any(z in b.get("douleurs", []) for b in recents)]
        zones_txt = " et ".join(z.lower() for z in douleurs)
        if repetees:
            for s in a_venir[:7]:
                if s.jour - aujourd_hui <= timedelta(days=7):
                    if s.genre in QUALITE:
                        aj[s.jour.isoformat()] = {"type": "footing", "minutes": 30,
                                                  "note": f"Douleur répétée ({zones_txt}) : pas d'intensité cette semaine."}
                    elif s.genre in ("long", "footing"):
                        aj[s.jour.isoformat()] = {"type": "raccourcir", "facteur": 0.7,
                                                  "note": f"Douleur répétée ({zones_txt}) : volume réduit."}
            phrases.append(f"Deuxième alerte pour : {zones_txt}. Cette semaine : volume réduit de 30 % et zéro "
                           "intensité. Si ça persiste, montre-le à un·e kiné ou un médecin.")
            titre = "On ménage sérieusement."
        else:
            longue = next((s for s in a_venir if s.genre == "long"), None)
            impact = {"pied", "achille", "mollet"} & {z.lower() for z in douleurs}
            footing = next((s for s in a_venir if s.genre == "footing"), None)
            if impact and bilan.get("velo_possible") and footing:
                aj[footing.jour.isoformat()] = {"type": "velo",
                                                "note": f"Douleur ({zones_txt}) : ce footing passe en vélo, zéro impact."}
                phrases.append(f"Ton prochain footing ({footing.jour.strftime('%d/%m')}) passe en vélo : "
                               "même effort, zéro impact pour ta jambe.")
            if longue:
                aj[longue.jour.isoformat()] = {"type": "raccourcir", "facteur": 0.8,
                                               "note": f"Douleur signalée ({zones_txt}) : sortie longue raccourcie."}
                phrases.append(f"Noté pour : {zones_txt}. Ta prochaine sortie longue passe à "
                               f"{fmt_duree(longue.minutes * 0.8 * 60, court=True)}, et le prochain renfo cible cette zone.")
            else:
                phrases.append(f"Noté pour : {zones_txt}. Le prochain renfo cible cette zone.")
            titre = "Noté, on ménage."
        etat.setdefault("douleurs_recentes", {})
        for z in douleurs:
            etat["douleurs_recentes"][z.lower()] = aujourd_hui.isoformat()
    else:
        titre = "Bien joué !"

    # 2. Ressenti vs attendu
    hist = [b for b in etat["bilans"].values()
            if date.fromisoformat(b["jour"]) >= aujourd_hui - timedelta(days=10) and b.get("type") == "course"]
    trop_dur = [b for b in hist if NIVEAU.get(b["ressenti"], 3) - ATTENDU.get(b.get("genre"), 3) >= 2]
    trop_facile = [b for b in hist if b.get("genre") in QUALITE
                   and NIVEAU.get(b["ressenti"], 3) - ATTENDU.get(b.get("genre"), 3) <= -2]
    if ecart >= 2 and len(trop_dur) >= 2 and not _regle_deja(etat, f"dur-{aujourd_hui.isoformat()}"):
        f["allure"] = round(min(1.06, f.get("allure", 1.0) * 1.02), 4)
        f["volume"] = round(max(0.7, f.get("volume", 1.0) * 0.92), 3)
        phrases.append("Deux séances bien plus dures que prévu en 10 jours : j'allège le volume de 8 % "
                       "et je ralentis un peu tes allures.")
        titre = "On souffle un peu."
    elif ecart >= 2:
        phrases.append("Plus dur que prévu. Une fois, ça arrive : si ça se répète, j'allège.")
    elif ecart <= -2 and genre in QUALITE and len(trop_facile) >= 2 and not _regle_deja(etat, f"facile-{aujourd_hui.isoformat()}"):
        f["allure"] = round(max(0.95, f.get("allure", 1.0) * 0.985), 4)
        phrases.append("Deux séances de qualité très faciles : tes allures accélèrent d'environ 1,5 %. Bravo !")
        titre = "Tu progresses !"

    # 3. Allures tenues ?
    conf = bilan.get("conformite") or []
    lents = [c for c in conf if c["ton"] == "lent"]
    if conf and not lents and not douleurs:
        phrases.insert(0, "Blocs tenus" + (f", ressenti « {dict(RESSENTIS)[bilan['ressenti']].lower()} » "
                                           "comme prévu." if ecart in (-1, 0, 1) else "."))
    elif len(lents) >= max(2, len(conf) // 2 + 1):
        phrases.append("Plusieurs blocs plus lents que la cible : rien de grave, ça arrive avec la fatigue ou la chaleur.")

    if not phrases:
        prochaine = next(iter(a_venir), None)
        if prochaine:
            phrases.append(f"On ne touche à rien. Prochaine sortie : {prochaine.titre.lower()}.")
        else:
            phrases.append("On ne touche à rien.")
    texte = " ".join(phrases)
    _noter(etat, aujourd_hui, texte, f"bilan-{bilan['cle']}")
    return titre, texte


def douleurs_recentes(etat: dict, aujourd_hui: date, jours: int = 21) -> list[str]:
    res = []
    for z, d in etat.get("douleurs_recentes", {}).items():
        if date.fromisoformat(d) >= aujourd_hui - timedelta(days=jours):
            res.append(z)
    return res


def bilans_en_attente(etat: dict, liens: dict, libres: list, plan: Plan, aujourd_hui: date) -> list[tuple[Optional[Seance], dict]]:
    """Sorties des 3 derniers jours sans bilan."""
    faits = etat.get("bilans", {})
    res = []
    for s in plan.seances():
        act = liens.get(s.ident)
        if act and aujourd_hui - timedelta(days=3) <= act["date"] <= aujourd_hui and str(act["id"]) not in faits:
            res.append((s, act))
    for act in libres:
        if aujourd_hui - timedelta(days=3) <= act["date"] <= aujourd_hui and str(act["id"]) not in faits:
            res.append((None, act))
    return res
