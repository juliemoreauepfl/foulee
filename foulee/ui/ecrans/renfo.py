"""Séance de renfo (selon le matériel du jour), fiche d'exercice et bibliothèque."""
from __future__ import annotations

from datetime import date

import streamlit as st

from ...engine import ajustement as AJ
from ...engine import renfo as R
from ...engine.seances import fmt_date
from .. import etat as E
from .. import theme as T
from ..commun import carte_exo, entete, html, titre

ETIQUETTES = {"Rien": R.RIEN, "Élastiques": R.ELASTIQUE, "Kettlebell": R.KETTLEBELL}
COEUR = ('<svg width="15" height="15" viewBox="0 0 24 24" role="img" aria-label="Favori" style="vertical-align:-2px;margin-left:6px">'
         '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="#E0442B"/></svg>')


def _prefs():
    return E.etat().setdefault("renfo", {"favoris": [], "bannis": [], "materiel": R.RIEN})


def _retour(label: str, page: str, cle: str):
    if st.button(f"‹ {label}", key=f"lien_{cle}"):
        E.aller(page)


# ------------------------------------------------------------ séance
def seance():
    e = E.etat()
    pr = _prefs()
    auj = E.aujourd_hui()
    jour: date = st.session_state.get("renfo_jour") or auj
    entete(fmt_date(jour))
    _retour("Retour", "semaine" if jour != auj else "aujourdhui", "retour_renfo")

    inverse = {v: k for k, v in ETIQUETTES.items()}
    lib = st.segmented_control("Aujourd'hui, j'ai sous la main :", list(ETIQUETTES),
                               default=inverse.get(pr.get("materiel", R.RIEN), "Rien"), key="materiel")
    choix = ETIQUETTES.get(lib or "Rien", R.RIEN)
    if choix != pr.get("materiel"):
        pr["materiel"] = choix
        E.sauver()

    douleurs = AJ.douleurs_recentes(e, auj)
    exos = R.composer_seance(choix, jour, pr["favoris"], pr["bannis"], douleurs)
    nom, pitch = R.NOMS_SEANCES[choix]
    titre(T.esc(nom), pitch, 34)
    if douleurs:
        html(f'<div class="f-bleu">Séance orientée pour protéger : {T.esc(", ".join(douleurs))}.</div>')
    html(f'<p class="f-sous" style="margin:0">{len(exos)} exercices · 3 tours · ~{R.duree_estimee(exos)} min</p>')

    for k, x in enumerate(exos):
        carte_exo(x, COEUR if x.id in pr["favoris"] else "")
        if st.button("Voir la fiche", key=f"petit_fiche_{x.id}"):
            E.aller("exercice", exo_liste=[y.id for y in exos], exo_index=k, exo_mode="fiche", page_avant_fiche="renfo")
    if jour.isoformat() in e.get("renfo_faits", {}):
        html(f'<div class="f-carte">{T.tag("Faite", T.VERT_FOND, T.VERT_TEXTE)} <span class="f-sous">Bravo, séance enregistrée.</span></div>')
    elif st.button("C'est parti", key="accent_go"):
        st.session_state.series = {}
        E.aller("exercice", exo_liste=[y.id for y in exos], exo_index=0, exo_mode="seance", page_avant_fiche="renfo")
    if st.button("Mes exercices (favoris, bannis)", key="lien_biblio"):
        E.aller("biblio")


# ------------------------------------------------------------ fiche
def exercice():
    e = E.etat()
    pr = _prefs()
    liste = st.session_state.get("exo_liste") or [R.BIBLIOTHEQUE[0].id]
    i = min(st.session_state.get("exo_index", 0), len(liste) - 1)
    mode = st.session_state.get("exo_mode", "fiche")
    x = R.PAR_ID[liste[i]]
    entete(f"Exercice {i + 1} / {len(liste)}" if mode == "seance" else "Fiche exercice")
    _retour("Séance" if st.session_state.get("page_avant_fiche") != "biblio" else "Mes exercices",
            st.session_state.get("page_avant_fiche") or "renfo", "retour_exo")

    titre(T.esc(x.nom), x.phrase, 34)
    html(f'<div class="f-carte" style="padding:10px;display:flex;justify-content:center">'
         f'<img src="{T.image_exo(x.image)}" alt="{T.esc(x.nom)}" style="width:min(240px,70%);border-radius:24px"></div>')
    etapes = "".join(f'<div class="f-tuile"><div class="f-titre" style="font-size:22px">{k}</div>'
                     f'<div style="font-size:13px;line-height:1.35;margin-top:4px">{T.esc(t)}</div></div>'
                     for k, t in enumerate(x.etapes, 1))
    html(f'<div class="f-grille3">{etapes}</div>')
    html(f'<div class="f-bleu"><b>Pourquoi pour courir ?</b> {T.esc(x.pourquoi)}</div>')
    html(f'''<div class="f-grille2">
      <div style="background:{T.ORANGE_FOND};color:{T.ORANGE_TEXTE};border-radius:18px;padding:10px 12px;font-size:13px;line-height:1.35"><b>Oups :</b> {T.esc(x.oups)}</div>
      <div style="background:{T.VERT_FOND};color:{T.VERT_TEXTE};border-radius:18px;padding:10px 12px;font-size:13px;line-height:1.35"><b>Trop facile ?</b> {T.esc(x.plus_dur)}</div></div>''')
    _boutons_gout(x, "fiche")

    if mode == "seance":
        series = st.session_state.setdefault("series", {})
        n = series.get(x.id, 0)
        points = "".join(f'<span style="width:14px;height:14px;border-radius:999px;display:block;'
                         f'{"background:" + E.accent() if k < n else "box-shadow: inset 0 0 0 2px #8B877F"}"></span>' for k in range(3))
        entete_txt = "3 séries sur 3" if n >= 3 else f"Série {n + 1} sur 3"
        gros = "Bien joué !" if n >= 3 else x.reps.split("×")[-1].strip()
        html(f'''<div class="f-sombre"><div class="f-ligne"><div><div class="f-sous">{entete_txt}</div>
          <div class="f-titre" style="font-size:26px">{T.esc(gros)}</div></div>
          <div style="display:flex;gap:6px">{points}</div></div></div>''')
        if n < 3:
            if st.button("Série faite · repos 45 s", key="accent_serie"):
                series[x.id] = n + 1
                st.rerun()
        elif i + 1 < len(liste):
            if st.button(f"Au suivant : {R.PAR_ID[liste[i + 1]].nom.lower()}", key="accent_suivant"):
                E.aller("exercice", exo_index=i + 1)
        else:
            _fin_seance(e, liste)
    else:
        c1, c2 = st.columns(2)
        with c1:
            if i > 0 and st.button("‹ Précédent", key="petit_exo_prec"):
                E.aller("exercice", exo_index=i - 1)
        with c2:
            if i + 1 < len(liste) and st.button("Suivant ›", key="petit_exo_suiv"):
                E.aller("exercice", exo_index=i + 1)


def _fin_seance(e, liste):
    html(f'<div class="f-accent"><div class="f-titre" style="font-size:26px">Séance terminée !</div>'
         f'<p style="margin:4px 0 0;font-size:14px">Comment c\'était ?</p></div>')
    ressenti = st.segmented_control("Ressenti", [lib for _, lib in AJ.RESSENTIS], key="ressenti_renfo",
                                    label_visibility="collapsed")
    if st.button("Enregistrer", key="accent_fin_renfo", disabled=not ressenti):
        jour = (st.session_state.get("renfo_jour") or E.aujourd_hui()).isoformat()
        cle_ressenti = next(k for k, lib in AJ.RESSENTIS if lib == ressenti)
        e.setdefault("renfo_faits", {})[jour] = {"exos": liste, "materiel": _prefs().get("materiel"),
                                                 "ressenti": cle_ressenti}
        if cle_ressenti in ("dur", "lumiere"):
            texte = "Renfo costaud aujourd'hui : demain, footing tout en douceur si tu en as un."
        else:
            texte = "Renfo dans la poche. Tes tendons te remercient."
        e.setdefault("notes", []).append({"jour": jour, "texte": texte, "cle": f"renfo-{jour}"})
        E.sauver()
        E.invalider()
        st.session_state.series = {}
        st.toast("Séance de renfo enregistrée")
        E.aller("aujourdhui")


def _boutons_gout(x, suffixe: str):
    pr = _prefs()
    fav, ban = x.id in pr["favoris"], x.id in pr["bannis"]
    c1, c2 = st.columns(2)
    with c1:
        if st.button("♥ Favori" if fav else "♡ J'aime", key=f"petit_fav_{suffixe}_{x.id}",
                     type="primary" if fav else "secondary"):
            pr["favoris"] = [i for i in pr["favoris"] if i != x.id] if fav else pr["favoris"] + [x.id]
            if not fav:
                pr["bannis"] = [i for i in pr["bannis"] if i != x.id]
            E.sauver()
            st.rerun()
    with c2:
        if st.button("Remettre" if ban else "Bof, plus jamais", key=f"petit_ban_{suffixe}_{x.id}",
                     type="primary" if ban else "secondary"):
            pr["bannis"] = [i for i in pr["bannis"] if i != x.id] if ban else pr["bannis"] + [x.id]
            if not ban:
                pr["favoris"] = [i for i in pr["favoris"] if i != x.id]
            E.sauver()
            st.rerun()


# ------------------------------------------------------------ bibliothèque
FILTRES = {"Tous": None, "Sans matériel": R.RIEN, "Élastiques": R.ELASTIQUE, "Kettlebell": R.KETTLEBELL,
           "Favoris": "fav", "Bannis": "ban"}


def bibliotheque():
    pr = _prefs()
    entete("Réglages renfo")
    _retour("Séance", "renfo", "retour_biblio")
    titre("Mes exercices", "Le coach pioche ici. Un cœur : il le ressort plus souvent. "
          "Un « bof » : il ne te le propose plus jamais.", 36)
    f = st.segmented_control("Filtrer", list(FILTRES), default="Tous", key="filtre_biblio",
                             label_visibility="collapsed")
    cible = FILTRES.get(f or "Tous")
    nf, nb = len(pr["favoris"]), len(pr["bannis"])
    html(f'<p class="f-sous" style="margin:0">{len(R.BIBLIOTHEQUE)} exercices · {nf} favori{"s" if nf > 1 else ""} · '
         f'{nb} banni{"s" if nb > 1 else ""}</p>')
    for x in R.BIBLIOTHEQUE:
        if cible == "fav" and x.id not in pr["favoris"]:
            continue
        if cible == "ban" and x.id not in pr["bannis"]:
            continue
        if cible in (R.RIEN, R.ELASTIQUE, R.KETTLEBELL) and x.materiel != cible:
            continue
        couleurs = {R.RIEN: (T.ORANGE_FOND, T.ORANGE_TEXTE), R.ELASTIQUE: (T.VERT_FOND, T.VERT_TEXTE),
                    R.KETTLEBELL: ("#FFF1C7", "#7A5600")}[x.materiel]
        etiquettes = (T.tag(R.NOMS_MATERIEL[x.materiel], *couleurs) + " " + T.tag(x.zone, T.CREME, T.GRIS_TEXTE)
                      + (" " + T.tag("Banni", T.ENCRE, T.BLANC) if x.id in pr["bannis"] else ""))
        opacite = "opacity:.55;" if x.id in pr["bannis"] else ""
        html(f'''<div class="f-exo" style="{opacite}"><img src="{T.image_exo(x.image)}" alt="{T.esc(x.nom)}" style="width:60px;height:60px">
          <div style="flex:1;display:flex;flex-direction:column;gap:4px"><span class="f-exo-nom" style="font-size:16px">{T.esc(x.nom)}
          {COEUR if x.id in pr["favoris"] else ""}</span><div>{etiquettes}</div></div></div>''')
        _boutons_gout(x, "biblio")
        if st.button("Voir la fiche", key=f"lien_fiche_b_{x.id}"):
            st.session_state.page_avant_fiche = "biblio"
            E.aller("exercice", exo_liste=[x.id], exo_index=0, exo_mode="fiche")
