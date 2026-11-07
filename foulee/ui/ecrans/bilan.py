"""« Comment c'était ? » : comparaison prévu / réalisé, ressenti, douleur, réponse du coach."""
from __future__ import annotations

import streamlit as st

from ...data import demo
from ...data.fitfile import lire_tours
from ...engine import ajustement as AJ
from ...engine.seances import fmt_date, fmt_duree, fmt_km
from .. import etat as E
from .. import theme as T
from ..commun import entete, html, titre


def _tours(act: dict, seance) -> list[dict]:
    if seance is None:
        return []
    if E.etat().get("mode") == "demo":
        return demo.tours_simules(seance, str(act["id"]))
    cache = st.session_state.setdefault("tours_cache", {})
    if act["id"] in cache:
        return cache[act["id"]]
    tours = []
    if E.connecte() and not str(act["id"]).startswith(("fichier-", "manuel-")):
        try:
            contenu = E.client().fichier_activite(act["id"])
            tours = lire_tours(contenu) if contenu else []
        except Exception:
            tours = []
    cache[act["id"]] = tours
    return tours


def afficher():
    e = E.etat()
    ctx = E.contexte()
    act = st.session_state.get("bilan_act")
    if not act:
        E.aller("aujourdhui")
    ident = st.session_state.get("bilan_seance")
    seance = next((s for s in ctx.plan.seances() if s.ident == ident), None)
    entete(fmt_date(act["date"]))
    if st.button("‹ Aujourd'hui", key="lien_retour_bilan"):
        E.aller("aujourdhui")

    reponse = st.session_state.get("bilan_reponse")
    if reponse:
        titre("Message<br>reçu !", "", 36)
        html(f'<div class="f-bleu"><div class="f-titre" style="font-size:20px;color:{T.BLEU_TEXTE}">{T.esc(reponse[0])}</div>'
             f'<p style="margin:6px 0 0">{T.esc(reponse[1])}</p></div>')
        if st.button("Retour à aujourd'hui", key="accent_fin_bilan"):
            st.session_state.pop("bilan_reponse", None)
            E.aller("aujourdhui")
        return

    titre("Comment<br>c'était ?", "", 36)
    nom = seance.titre if seance else act.get("nom", "Course")
    fc = f'{int(act["fc_moy"])}' if act.get("fc_moy") else "–"
    tours = _tours(act, seance)
    conf = AJ.conformite(seance, tours) if seance else []
    lignes = ""
    for c in conf:
        fond, coul = {"ok": (T.VERT_FOND, T.VERT_TEXTE), "lent": (T.ORANGE_FOND, T.ORANGE_TEXTE),
                      "vite": (T.BLEU_CLAIR, T.BLEU)}[c["ton"]]
        lignes += (f'<li><span>{c["bloc"]} · prévu {c["prevu"]}</span>'
                   f'<span>{T.tag(c["reel"] + " · " + c["statut"], fond, coul)}</span></li>')
    html(f'''<div class="f-sombre"><div class="f-ligne"><span class="f-titre" style="font-size:20px">{T.esc(nom)}</span>
      <span class="f-sous">trouvée sur ta montre</span></div>
      <div class="f-grille3" style="margin-top:10px">
        <div><div class="f-sous">Distance</div><div class="f-chiffre">{fmt_km(act["distance_km"])}</div></div>
        <div><div class="f-sous">Durée</div><div class="f-chiffre">{fmt_duree(act["duree_s"])}</div></div>
        <div><div class="f-sous">FC moy.</div><div class="f-chiffre">{fc}</div></div></div>
      {"<ol class='f-etapes'>" + lignes + "</ol>" if lignes else ""}</div>''')

    libelles = [lib for _, lib in AJ.RESSENTIS]
    ressenti = st.segmented_control("Ton ressenti", libelles, key="bilan_ressenti")
    if ressenti:
        niveau = libelles.index(ressenti) + 1
        html(f'<div style="display:flex;justify-content:center">{T.visage_svg(niveau, 72)}</div>')
    douleurs = st.pills("Une douleur ?", AJ.ZONES, selection_mode="multi", key="bilan_douleurs")
    mot = st.text_area("Un mot pour le coach ? (facultatif)", key="bilan_mot", height=80)

    if st.button("Envoyer au coach", key="accent_envoyer", disabled=not ressenti):
        cle_r = next(k for k, lib in AJ.RESSENTIS if lib == ressenti)
        bilan = {"cle": str(act["id"]), "jour": act["date"].isoformat() if hasattr(act["date"], "isoformat") else str(act["date"]),
                 "type": "course", "genre": seance.genre if seance else "footing", "ressenti": cle_r,
                 "douleurs": list(douleurs or []), "mot": mot, "conformite": conf,
                 "velo_possible": bool(ctx.profil.velo_semaine)}
        rep = AJ.traiter_bilan(e, ctx.plan, bilan, ctx.aujourd_hui)
        E.sauver()
        E.invalider()
        for k in ("bilan_ressenti", "bilan_douleurs", "bilan_mot"):
            st.session_state.pop(k, None)
        st.session_state.bilan_reponse = rep
        st.rerun()
