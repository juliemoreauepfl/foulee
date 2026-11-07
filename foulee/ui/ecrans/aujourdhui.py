"""Écran d'accueil : météo intérieure, séance du jour, bilan à faire."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from ...engine.seances import fmt_date, fmt_duree, fmt_km
from .. import etat as E
from .. import theme as T
from ..commun import bouton_fit, boutons_velo, carte_seance, mesures_du_jour, entete, html, jour_txt, nav, note_coach, tag_seance, tuiles

ACCROCHES = {
    "soleil": "Ton corps dit :<br>on y va.",
    "eclaircies": "On y va,<br>à l'écoute.",
    "nuages": "Aujourd'hui,<br>on y va mollo.",
    "orage": "Aujourd'hui,<br>on récupère.",
    "voile": "Prudence<br>aujourd'hui.",
    "inconnu": "On continue<br>sur la lancée ?",
}


def afficher():
    e = E.etat()
    ctx = E.contexte()
    auj = ctx.aujourd_hui
    entete(fmt_date(auj))
    prenom = e.get("prenom") or ""
    html(f'<div><p class="f-sous" style="margin:0;font-size:15px">Salut{" " + T.esc(prenom) if prenom else ""},</p>'
         f'<h1 class="f-titre" style="font-size:34px;margin:2px 0 0">{ACCROCHES.get(ctx.meteo.etat, ACCROCHES["inconnu"])}</h1></div>')
    nav("aujourdhui")

    if e.get("mode") == "demo":
        html('<div class="f-bleu">Mode démo : données inventées. Branche ta clé Garmin dans les Réglages quand tu veux.</div>')
    for n in [n for n in e.get("notes", []) if n["jour"] == auj.isoformat()][-2:]:
        note_coach(n["texte"])

    # Bilans à faire
    for k, (s, act) in enumerate(ctx.en_attente[:2]):
        nom = s.titre if s else act.get("nom", "Course")
        quand = "ce matin" if act["date"] == auj else fmt_date(act["date"])
        html(f'<div class="f-carte" style="box-shadow: inset 0 0 0 2px {T.ENCRE}"><div class="f-ligne">'
             f'<div><div class="f-sous">Nouvelle sortie trouvée · {T.esc(quand)}</div>'
             f'<div class="f-titre" style="font-size:20px;margin-top:2px">{T.esc(nom)}</div></div>'
             f'<span class="f-sous">{fmt_km(act["distance_km"])}</span></div></div>')
        if st.button("Comment c'était ?", key=f"accent_bilan_{k}"):
            E.aller("bilan", bilan_act=act, bilan_seance=s.ident if s else None)

    # Météo intérieure
    m = ctx.meteo
    detail = ""
    if m.derniere_nuit and m.zone_basse:
        detail = f"VFC {m.derniere_nuit:.0f} ms · ta zone {m.zone_basse:.0f}–{m.zone_haute:.0f}.<br>"
    html(f'''<div class="f-accent" style="display:flex;align-items:center;gap:14px">{T.meteo_svg(m.etat)}
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px">Météo intérieure</span>
        <span class="f-titre" style="font-size:26px">{T.esc(m.titre)}</span>
        <span style="font-size:13px;line-height:1.35">{detail}{T.esc(m.texte)}</span></div></div>''')

    # Séance(s) du jour
    seances = ctx.seances_du_jour()
    courses = [s for s in seances if s.sport in ("course", "course_cible", "velo")]
    renfos = [s for s in seances if s.sport == "renfo"]
    for s in courses:
        fait = ctx.liens.get(s.ident)
        carte_seance(s, "Séance du jour" if s.sport != "velo" else "Vélo du jour", fait)
        if not fait:
            (boutons_velo if s.sport == "velo" else bouton_fit)(s, s.ident)
    for s in renfos:
        faite = auj.isoformat() in e.get("renfo_faits", {})
        html(f'''<div class="f-carte"><div class="f-ligne"><span>{tag_seance(s)}</span>
          <span class="f-sous">~20 min</span></div>
          <div class="f-titre" style="font-size:25px;margin-top:10px">Renfo du jour</div>
          <div class="f-sous" style="margin-top:2px">{"Faite, bravo !" if faite else "5 exercices, tu choisis ton matériel."}</div></div>''')
        if not faite and st.button("Ouvrir la séance de renfo", key="renfo_jour", type="primary"):
            E.aller("renfo", renfo_jour=auj)
    if not seances:
        prochaine = next((s for s in ctx.plan.seances() if s.jour > auj), None)
        suite = f"Prochaine : {jour_txt(prochaine.jour, auj).lower()}, {prochaine.titre.lower()}." if prochaine else ""
        html(f'<div class="f-carte"><div class="f-titre" style="font-size:25px">Repos</div>'
             f'<p class="f-sous" style="margin:6px 0 0;line-height:1.4">Les muscles se construisent pendant la récup. '
             f'Marche, étire-toi, dors bien. {T.esc(suite)}</p></div>')

    # Tuiles
    som = ctx.donnees.sommeil
    nuit = som[som["date"] <= auj].tail(1) if som is not None and not som.empty else None
    h = f'{fmt_duree(float(nuit.iloc[0]["heures"]) * 3600, court=True)}' if nuit is not None and not nuit.empty else "–"
    fc = f'{int(nuit.iloc[0]["fc_repos"])} bpm' if nuit is not None and not nuit.empty and nuit.iloc[0]["fc_repos"] else "–"
    tsb = ctx.charge["fraicheur"].iloc[-1] if not ctx.charge.empty else 0
    q = ctx.donnees.quotidien
    if fc == "–" and q is not None and not q.empty and "fc_repos" in q and q["fc_repos"].notna().any():
        fc = f'{int(q["fc_repos"].dropna().iloc[-1])} bpm'
    tuiles([("Sommeil", h, T.ENCRE), ("FC repos", fc, T.ENCRE),
            ("Fraîcheur", f"{tsb:+.0f}", T.BLEU if tsb >= 0 else T.ORANGE_TEXTE)])
    bonus = mesures_du_jour(q, auj, ["bb_max", "stress", "pas", "recharge_ans", "spo2"])[:3]
    if len(bonus) >= 2:
        tuiles(bonus)
