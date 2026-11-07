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
                               round(m * 60 / ((lo + hi) / 2), 1), m, aj.get("note", ""), allegee=True,
                               origine=s.origine)
                elif aj["type"] == "velo":
                    from .velo import FabriqueVelo
                    origine = s.origine
                    s = FabriqueVelo(getattr(plan, "ftp", None), getattr(plan, "fc_max", None)).remplacer_footing(s)
                    s.note, s.origine = aj.get("note", s.note), origine
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


# ------------------------------------------------------------ déplacer une séance
DURES = QUALITE | {"long", "course", "velo_tempo"}


def appliquer_deplacements(plan: Plan, deplacements: dict) -> Plan:
    """deplacements : {identifiant d'origine : nouvelle date ISO}. Toujours dans la même semaine."""
    ordre = {"course": 0, "course_cible": 0, "velo": 1, "renfo": 2}
    for sem in plan.semaines:
        for s in sem.seances:
            s.origine = s.origine or s.ident
            cible = (deplacements or {}).get(s.origine)
            if cible:
                j = date.fromisoformat(cible)
                if sem.debut <= j < sem.debut + timedelta(days=7):
                    s.jour = j
        sem.seances.sort(key=lambda x: (x.jour, ordre.get(x.sport, 3)))
    return plan


def _meme_type(a: Seance, b: Seance) -> bool:
    groupe = lambda x: "velo" if x.sport == "velo" else ("renfo" if x.sport == "renfo" else "course")
    return groupe(a) == groupe(b)


def deplacer(etat: dict, plan: Plan, seance: Seance, cible: date) -> str:  # noqa: C901
    """Déplace une séance dans sa semaine. Si une séance du même type est déjà prévue ce
    jour-là, les deux s'échangent. Retourne un avertissement éventuel."""
    dep = etat.setdefault("deplacements", {})
    sem = plan.semaine_de(seance.jour)
    if sem is None or not (sem.debut <= cible < sem.debut + timedelta(days=7)):
        return "On ne peut déplacer une séance que dans sa semaine."
    autre = next((x for x in sem.seances if x.jour == cible and x is not seance and _meme_type(x, seance)), None)
    ancien = seance.jour
    dep[seance.origine or seance.ident] = cible.isoformat()
    if autre:
        dep[autre.origine or autre.ident] = ancien.isoformat()
    # Garde-fou : deux séances dures qui se suivent ?
    nouveaux = {id(seance): cible}
    if autre:
        nouveaux[id(autre)] = ancien
    durs = {nouveaux.get(id(x), x.jour) for x in sem.seances if x.genre in DURES}
    if any((j + timedelta(days=1)) in durs for j in durs):
        return "Attention : deux séances dures se suivent maintenant. Si tu peux, garde un jour facile entre les deux."
    return ""


# ------------------------------------------------------------ annuler la séance du jour
RAISONS = ["Fatigue", "Pas le temps", "Malade", "Douleur", "Météo"]


def annuler(etat: dict, plan: Plan, seance: Seance, aujourd_hui: date, raison: str = "") -> str:
    """Annule une séance. Une séance clé (qualité, sortie longue) prend la place d'un footing
    plus tard dans la semaine si c'est possible sans coller deux séances dures ; un footing
    annulé n'est pas rattrapé (on ne rattrape jamais du volume). Retourne le message du coach."""
    ann = etat.setdefault("annulations", {})
    cle = seance.origine or seance.ident
    if cle in ann:  # c'était déjà une séance reportée : cette fois, on la laisse tomber
        ann[cle]["definitif"] = True
        txt = f"{_nom(seance)} annulée pour de bon cette semaine. On repart sur la suite du plan."
        _noter(etat, aujourd_hui, txt, f"annul-{cle}-def")
        return txt
    sem = plan.semaine_de(seance.jour)
    remplace = None
    malade = raison in ("Malade", "Douleur")
    if sem and seance.sport == "course" and seance.genre in QUALITE | {"long"} and not malade:
        durs = {x.jour for x in sem.seances if x.genre in DURES and x is not seance}
        for x in sem.seances:
            if (x.sport == "course" and x.genre == "footing" and x.jour > aujourd_hui
                    and x.jour - timedelta(days=1) not in durs and x.jour + timedelta(days=1) not in durs):
                remplace = x
                break
    ann[cle] = {"jour": seance.jour.isoformat(), "raison": raison, "le": aujourd_hui.isoformat(),
                "remplace": (remplace.origine or remplace.ident) if remplace else None}
    if remplace:
        txt = (f"{_nom(seance)} annulée. Je la déplace au {_jour(remplace.jour)} à la place du footing : "
               "c'est la séance la plus utile de ta semaine.")
    elif seance.sport == "course" and seance.genre in QUALITE | {"long"} and not malade:
        txt = (f"{_nom(seance)} annulée. Pas de place pour la caser cette semaine sans enchaîner deux séances dures : "
               "on la laisse filer, le plan continue normalement.")
    elif seance.sport == "renfo":
        txt = "Renfo annulé. Pas grave : le prochain arrive vite."
    else:
        txt = f"{_nom(seance)} annulé. On ne rattrape pas : le plan continue normalement."
    if malade:
        aj = etat.setdefault("ajustements", {})
        for s in plan.seances():
            if aujourd_hui < s.jour <= aujourd_hui + timedelta(days=3) and s.sport == "course" and s.genre in QUALITE | {"long"}:
                aj[s.jour.isoformat()] = {"type": "footing", "minutes": 30,
                                          "note": f"Reprise en douceur après « {raison.lower()} » : footing tranquille."}
        txt += (" Les 3 prochains jours : pas d'intensité, juste du footing tranquille si tu te sens bien."
                + (" Si la douleur dure, montre-la à un·e kiné." if raison == "Douleur" else
                   " Si tu as de la fièvre, pas de course du tout."))
    _noter(etat, aujourd_hui, txt, f"annul-{cle}")
    return txt


def retablir(etat: dict, cle: str) -> None:
    a = (etat.get("annulations") or {}).pop(cle, None)
    if a:
        etat["notes"] = [n for n in etat.get("notes", []) if not n.get("cle", "").startswith(f"annul-{cle}")]


def appliquer_annulations(plan: Plan, annulations: dict) -> Plan:
    if not annulations:
        return plan
    ordre = {"course": 0, "course_cible": 0, "velo": 1, "renfo": 2}
    for sem in plan.semaines:
        par_origine = {(x.origine or x.ident): x for x in sem.seances}
        retirer, reportees = set(), set()
        for cle, a in annulations.items():
            s = par_origine.get(cle)
            if s is None:
                continue
            r = par_origine.get(a.get("remplace") or "")
            if r is not None and not a.get("definitif"):
                s.jour, s.reportee = r.jour, True
                s.note = f"Reportée ({a.get('raison', '').lower() or 'séance annulée'})." + (" " + s.note if s.note else "")
                reportees.add(id(s))
                retirer.add(id(r))
            else:
                retirer.add(id(s))
                if r is not None:
                    retirer.add(id(r))
        sem.seances = [x for x in sem.seances if id(x) not in retirer or id(x) in reportees]
        sem.seances.sort(key=lambda x: (x.jour, ordre.get(x.sport, 3)))
        sem.km = round(sum(x.km for x in sem.seances), 1)
    return plan


def _nom(s: Seance) -> str:
    return "Le renfo" if s.sport == "renfo" else s.titre.split("·")[0].strip()


def _jour(j: date) -> str:
    from .seances import JOURS
    return f"{JOURS[j.weekday()].lower()} {j.day}"


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
    annulees = [a for a in (etat.get("annulations") or {}).values()
                if aujourd_hui - timedelta(days=14) <= date.fromisoformat(a["le"]) < aujourd_hui]
    manquees = manquees + annulees
    passees = passees + annulees
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


# ------------------------------------------------------------ règles cardio
FACILES = {"footing", "long"}


def regles_cardio(etat: dict, plan: Plan, aujourd_hui: date) -> list[str]:
    """Ajuste le plan à partir de la FC mesurée pendant tes sorties (etat["cardio"])."""
    from statistics import median
    cardio = [c for c in (etat.get("cardio") or {}).values() if c.get("jour")]
    cardio.sort(key=lambda c: c["jour"])
    j = lambda c: date.fromisoformat(c["jour"])
    faciles = [c for c in cardio if c.get("genre") in FACILES and aujourd_hui - timedelta(days=42) <= j(c) <= aujourd_hui]
    f = etat.setdefault("facteurs", {"allure": 1.0, "volume": 1.0})
    aj = etat.setdefault("ajustements", {})
    sem = aujourd_hui.isocalendar()
    messages = []

    def dire(cle, txt):
        _noter(etat, aujourd_hui, txt, cle)
        messages.append(txt)

    # 1. Footings trop rapides : 2 des 4 derniers avec plus de 30 % du temps au-dessus de l'endurance
    recents = [c for c in faciles if j(c) >= aujourd_hui - timedelta(days=21)][-4:]
    vites = [c for c in recents if sum((c.get("pct") or [0] * 5)[2:]) > 30]
    if len(vites) >= 2 and not _regle_deja(etat, f"cardio-vite-{sem.year}-{sem.week}"):
        f["allure"] = round(min(1.06, f.get("allure", 1.0) * 1.01), 4)
        dire(f"cardio-vite-{sem.year}-{sem.week}",
             f"{len(vites)} de tes {len(recents)} derniers footings sont sortis trop haut en FC. Je ralentis un peu tes allures, "
             "et chaque séance affiche maintenant ta FC cible : reste dessous.")

    # 2. Dérive cardiaque sur les deux dernières sorties longues → la prochaine ne s'allonge pas
    longues = [c for c in faciles if c.get("genre") == "long" and c.get("derive") is not None][-2:]
    if len(longues) == 2 and all(c["derive"] > 5 for c in longues) and not _regle_deja(etat, f"cardio-derive-{sem.year}-{sem.week}"):
        prochaine = next((s for s in plan.seances() if s.genre == "long" and s.jour > aujourd_hui
                          and s.jour.isoformat() not in aj), None)
        if prochaine:
            aj[prochaine.jour.isoformat()] = {"type": "raccourcir", "facteur": 0.9,
                                              "note": "Dérive cardiaque sur tes deux dernières sorties longues : on consolide avant d'allonger."}
            dire(f"cardio-derive-{sem.year}-{sem.week}",
                 "Ta FC dérive en fin de sortie longue deux fois de suite : la prochaine est raccourcie de 10 % "
                 "pour consolider. Pense à boire et à partir plus doucement.")

    # 3. Fatigue cardiaque : FC anormalement haute pour la vitesse sur ta dernière sortie facile
    effs = [c["efficacite"] for c in faciles[:-1] if c.get("efficacite")]
    dern = faciles[-1] if faciles else None
    if (dern and dern.get("efficacite") and len(effs) >= 3 and (aujourd_hui - j(dern)).days <= 2
            and dern["efficacite"] < median(effs) * 0.93 and not _regle_deja(etat, f"cardio-fatigue-{dern['jour']}")):
        dure = next((s for s in plan.seances() if s.sport == "course" and s.genre in QUALITE
                     and aujourd_hui <= s.jour <= aujourd_hui + timedelta(days=3) and s.jour.isoformat() not in aj), None)
        txt = (f"Sur ta dernière sortie facile, ta FC était haute pour ta vitesse (efficacité {100 * (1 - dern['efficacite'] / median(effs)):.0f} % "
               "sous ton habitude) : signe de fatigue, de chaleur ou d'un virus qui traîne.")
        if dure:
            aj[dure.jour.isoformat()] = {"type": "footing", "minutes": 35,
                                         "note": "Cœur fatigué sur la dernière sortie : footing tranquille au lieu de la séance."}
            txt += f" {dure.titre.split('·')[0].strip()} remplacé par un footing tranquille."
        dire(f"cardio-fatigue-{dern['jour']}", txt)

    # 4. Progrès : à intensité facile, tu vas plus loin par battement qu'il y a un mois
    avant = [c["efficacite"] for c in faciles if c.get("efficacite") and j(c) < aujourd_hui - timedelta(days=14)]
    apres = [c["efficacite"] for c in faciles if c.get("efficacite") and j(c) >= aujourd_hui - timedelta(days=14)]
    cle = f"cardio-progres-{sem.year}-{sem.week // 4}"
    if len(avant) >= 3 and len(apres) >= 3 and median(apres) >= median(avant) * 1.05 and not _regle_deja(etat, cle):
        gain = 100 * (median(apres) / median(avant) - 1)
        f["allure"] = round(max(0.95, f.get("allure", 1.0) * 0.99), 4)
        dire(cle, f"Ton cœur progresse : à effort facile, tu vas {gain:.0f} % plus loin par battement qu'il y a un mois. "
                  "Tes allures accélèrent d'environ 1 %.")
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

    # 4. Fréquence cardiaque
    cardio = bilan.get("cardio") or {}
    alertes = [t for ton, t in cardio.get("messages", []) if ton == "attention"]
    if alertes and not douleurs:
        vites = [b for b in hist if b is not bilan and b.get("genre") in ("footing", "long")
                 and any("Un peu vite" in t for _, t in (b.get("cardio") or {}).get("messages", []))]
        if any("Un peu vite" in t for t in alertes) and vites:
            phrases.append("Deuxième footing trop rapide côté cardio : ralentis franchement, quitte à marcher dans les côtes. "
                           "Des footings trop rapides fatiguent sans faire progresser.")
        else:
            phrases.append(alertes[0].split(":")[0] + " côté cardio : détail dans l'analyse de la sortie.")

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
