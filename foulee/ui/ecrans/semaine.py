"""La semaine : compte à rebours, volume, séances et notes du coach."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from ...engine import vdot as V
from ...engine.plan import PHASES
from ...engine.seances import JOURS_COURTS, fmt_km
from .. import etat as E
from .. import theme as T
from ..commun import VELO_SVG, feter_si_besoin, jauge_km, entete, html, jour_txt, nav, note_coach

HALTERE = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#24399E" stroke-width="2.2" '
           'stroke-linecap="round" aria-hidden="true"><path d="M6 7v10M3 9.5v5M18 7v10M21 9.5v5M6 12h12"/></svg>')


def afficher():
    e = E.etat()
    ctx = E.contexte()
    auj = ctx.aujourd_hui
    plan = ctx.plan
    decal = st.session_state.get("decal_semaine", 0)
    idx_auj = next((i for i, s in enumerate(plan.semaines) if s.debut <= auj < s.debut + timedelta(days=7)), 0)
    idx = min(max(idx_auj + decal, 0), len(plan.semaines) - 1)
    sem = plan.semaines[idx]
    entete(f"Semaine {idx + 1} / {len(plan.semaines)}")
    nav("semaine")
    feter_si_besoin(ctx)

    # En-tête sombre
    p = ctx.profil
    forme = p.distance == "forme"
    j_moins = (p.date_course - auj).days if p.date_course else 0
    faits, prevus = ctx.km_semaine(sem)
    obj = f" · objectif {T.esc(_chrono(p.objectif_s))}" if p.objectif_s else ""
    html(f'''<div class="f-sombre"><div class="f-ligne">
      <span class="f-sous">{V.NOMS_DISTANCES[p.distance]}{obj}</span>
      <span class="f-titre" style="font-size:24px;color:{E.accent()}">{f"Sem. {idx % 4 + 1}/4" if forme else f"J-{max(j_moins, 0)}"}</span></div>
      <div class="f-sous" style="margin-top:4px">{("Semaine plus légère" if sem.phase == "base" else "Semaine de travail") if forme else "Phase : " + PHASES[sem.phase].lower()} · km courus / prévus</div>
      <div style="margin-top:6px">{jauge_km(faits, prevus, sombre=True)}</div></div>''')

    _graphe(ctx, idx, forme)

    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c1:
        if st.button("‹ Préc.", key="petit_prec", disabled=idx == 0):
            st.session_state.decal_semaine = decal - 1
            st.rerun()
    with c2:
        if decal != 0 and st.button("Cette semaine", key="petit_cette"):
            st.session_state.decal_semaine = 0
            st.rerun()
    with c3:
        if st.button("Suiv. ›", key="petit_suiv", disabled=idx >= len(plan.semaines) - 1):
            st.session_state.decal_semaine = decal + 1
            st.rerun()

    # Pastilles des jours
    cases = []
    for k in range(7):
        j = sem.debut + timedelta(days=k)
        du_jour = [s for s in sem.seances if s.jour == j]
        base = "f-pastille"
        if j == auj:
            style = f"background:{E.accent()};color:{T.ENCRE}"
        elif any(s.ident in ctx.liens for s in du_jour) or (j.isoformat() in e.get("renfo_faits", {})):
            style = f"background:{T.ENCRE};color:{T.BLANC}"
        elif not du_jour:
            style = f"background:transparent;color:{T.GRIS};border:1.5px dashed #B8B0A4"
        elif all(s.sport == "renfo" for s in du_jour):
            style = f"background:{T.BLEU};color:{T.BLANC}"
        else:
            style = f"background:{T.BLANC};color:{T.ENCRE}"
        cases.append(f'<div><span class="f-sous" style="font-size:12px">{JOURS_COURTS[k]}</span>'
                     f'<div class="{base}" style="{style}">{j.day}</div></div>')
    html(f'<div class="f-jours">{"".join(cases)}</div>')

    # Liste des séances
    for s in sem.seances:
        fait = ctx.liens.get(s.ident)
        if s.sport == "renfo":
            statut = _chip("Fait", "ok") if s.jour.isoformat() in e.get("renfo_faits", {}) else (
                _chip("À faire", "noir") if s.jour == auj else (_chip("Pas fait", "gris") if s.jour < auj else _chip("Prévu", "gris")))
            html(f'''<div class="f-carte" style="padding:10px 16px"><div class="f-ligne">
              <div style="display:flex;align-items:center;gap:12px"><span style="width:36px;height:36px;border-radius:12px;
              background:{T.BLEU_CLAIR};display:flex;align-items:center;justify-content:center">{HALTERE}</span>
              <div><div class="f-sous" style="font-size:12px">{T.esc(jour_txt(s.jour, auj))}</div>
              <div style="font-weight:600;font-size:15px">Renfo · ~20 min</div></div></div>{statut}</div></div>''')
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Ouvrir le renfo", key=f"petit_renfo_{s.jour.isoformat()}"):
                    E.aller("renfo", renfo_jour=s.jour)
            with c2:
                _deplacer(ctx, sem, s)
            continue
        if s.sport == "velo":
            statut = _chip("Fait", "ok") if fait else (_chip("À faire", "noir") if s.jour == auj else (
                _chip("Pas fait", "gris") if s.jour < auj else _chip("Prévu", "gris")))
            if s.allegee:
                statut = _chip("Remplace un footing", "bleu") + " " + statut
            html(f'''<div class="f-carte" style="padding:10px 16px"><div class="f-ligne">
              <div style="display:flex;align-items:center;gap:12px"><span style="width:36px;height:36px;border-radius:12px;
              background:#E8E3FF;display:flex;align-items:center;justify-content:center">{VELO_SVG}</span>
              <div><div class="f-sous" style="font-size:12px">{T.esc(jour_txt(s.jour, auj))}</div>
              <div style="font-weight:600;font-size:15px">{T.esc(s.titre)}</div></div></div><div>{statut}</div></div></div>''')
            if not fait:
                _deplacer(ctx, sem, s)
            continue
        if fait:
            statut = _chip("Fait", "ok")
            bilan = e.get("bilans", {}).get(str(fait["id"]))
            if bilan and bilan.get("ressenti") in ("dur", "lumiere") and s.genre in ("footing", "long"):
                statut = _chip("Un peu dur", "orange")
        elif s.jour == auj:
            statut = _chip("À faire", "noir")
        elif s.jour < auj:
            statut = _chip("Sautée", "gris")
        else:
            statut = _chip("Prévu", "gris")
        if s.allegee:
            statut = _chip("Allégée", "bleu") + " " + statut
        if s.reportee:
            statut = _chip("Reportée", "bleu") + " " + statut
        bord = f";box-shadow: inset 0 0 0 2px {T.ENCRE}" if s.jour == auj else ""
        km = f' · {fmt_km(fait["distance_km"])}' if fait else ""
        html(f'''<div class="f-carte" style="padding:10px 16px{bord}"><div class="f-ligne">
          <div><div class="f-sous" style="font-size:12px">{T.esc(jour_txt(s.jour, auj))}{km}</div>
          <div style="font-weight:600;font-size:15px">{T.esc(s.titre)}</div></div><div>{statut}</div></div></div>''')
        if not fait and s.sport == "course":
            _deplacer(ctx, sem, s)
        if fait and st.button("Voir ma FC pendant la sortie", key=f"petit_fc_{s.ident.replace('-', '_')}",
                              icon=":material/monitor_heart:"):
            E.aller("sortie", sortie_act=fait, sortie_seance=s.ident)

    fin = (sem.debut + timedelta(days=7)).isoformat()
    for cle, a in (e.get("annulations") or {}).items():
        if sem.debut.isoformat() <= a["jour"] < fin and (not a.get("remplace") or a.get("definitif")):
            nom = "Renfo" if cle.endswith("renfo") else cle.split("-", 3)[-1].capitalize()
            html(f'<div class="f-carte" style="padding:10px 16px;background:{T.CREME_FONCE}"><div class="f-ligne">'
                 f'<div><div class="f-sous" style="font-size:12px">{T.esc(jour_txt(__import__("datetime").date.fromisoformat(a["jour"]), auj))}</div>'
                 f'<div style="font-weight:600;font-size:15px;text-decoration:line-through">{T.esc(nom)}</div></div>'
                 f'{_chip("Annulée" + (" · " + a["raison"].lower() if a.get("raison") else ""), "gris")}</div></div>')

    if any(x.origine in e.get("deplacements", {}) for x in sem.seances):
        if st.button("Remettre les jours prévus par le coach", key=f"lien_reset_dep_{sem.debut.isoformat()}"):
            for x in sem.seances:
                e.get("deplacements", {}).pop(x.origine, None)
            E.sauver()
            E.invalider()
            st.rerun()

    notes = [n for n in e.get("notes", []) if sem.debut.isoformat() <= n["jour"] < (sem.debut + timedelta(days=7)).isoformat()]
    for n in notes[-3:]:
        note_coach(n["texte"])


def _deplacer(ctx, sem, s):
    """Petit menu pour changer le jour d'une séance (dans sa semaine)."""
    from ...engine import ajustement as AJ
    from ...engine.seances import JOURS
    auj = ctx.aujourd_hui
    if s.jour < auj:
        return
    jours = [sem.debut + timedelta(days=k) for k in range(7)]
    possibles = [j for j in jours if j >= auj and j != s.jour]
    if not possibles:
        return
    cle = (s.origine or s.ident).replace("-", "_")
    with st.popover("Changer de jour", icon=":material/swap_horiz:"):
        lib = {f"{JOURS[j.weekday()][:3]}. {j.day}": j for j in possibles}
        choix = st.segmented_control("Nouveau jour", list(lib), key=f"dep_{cle}_{s.jour.isoformat()}")
        if choix:
            occupe = [x for x in sem.seances if x.jour == lib[choix] and x is not s and AJ._meme_type(x, s)]
            if occupe:
                st.caption(f"Ce jour-là : {occupe[0].titre}. Les deux séances seront échangées.")
        if st.button("Déplacer", key=f"petit_dep_ok_{cle}", type="primary", disabled=not choix):
            alerte = AJ.deplacer(E.etat(), ctx.plan, s, lib[choix])
            E.sauver()
            E.invalider()
            st.toast(alerte or "Séance déplacée")
            st.rerun()


def _graphe(ctx, idx, forme):
    """Charge prévue / réalisée de chaque semaine jusqu'à l'objectif."""
    from ...engine.plan import charge_seance
    e = E.etat()
    auj = ctx.aujourd_hui
    lignes = []
    for i, sem in enumerate(ctx.plan.semaines):
        faite = None
        if sem.debut <= auj:
            faite = 0.0
            for s in sem.seances:
                act = ctx.liens.get(s.ident)
                if act:
                    faite += charge_seance(s, act["duree_s"] / 60)
                elif s.sport == "renfo" and s.jour.isoformat() in e.get("renfo_faits", {}):
                    faite += charge_seance(s)
        lignes.append({"prevue": sem.charge, "faite": faite, "phase": sem.phase, "courante": i == idx,
                       "jour_j": any(s.sport == "course_cible" for s in sem.seances)})
    # Le pic d'entraînement se lit hors semaine de course (la course elle-même pèse lourd)
    hors_course = [i for i, l in enumerate(lignes) if not l["jour_j"]] or list(range(len(lignes)))
    pic = max(hors_course, key=lambda i: lignes[i]["prevue"])
    titre = "Ton cycle de 12 semaines" if forme else "Ton plan jusqu'au jour J"
    sous = (f"Charge prévue par semaine. Pic en semaine {pic + 1}, puis affûtage pour arriver frais."
            if not forme else "Charge prévue par semaine : 3 semaines de travail, 1 plus légère.")
    html(f'''<div class="f-carte"><div class="f-ligne"><h2 class="f-titre" style="font-size:20px">{titre}</h2>
      <span class="f-sous">{len(lignes)} sem.</span></div>
      <div style="margin-top:6px">{T.graphe_plan(lignes, E.accent())}</div>
      {T.legende_phases([l["phase"] for l in lignes], E.accent())}
      <p class="f-sous" style="margin:4px 0 0;line-height:1.4">{sous}</p></div>''')


def _chip(txt, ton):
    couleurs = {"ok": (T.VERT_FOND, T.VERT_TEXTE), "noir": (T.ENCRE, T.BLANC), "gris": (T.CREME_FONCE, T.GRIS_TEXTE),
                "orange": (T.ORANGE_FOND, T.ORANGE_TEXTE), "bleu": (T.BLEU_CLAIR, T.BLEU)}
    return T.tag(txt, *couleurs[ton])


def _chrono(s):
    from ...engine.seances import fmt_duree
    return fmt_duree(s)
