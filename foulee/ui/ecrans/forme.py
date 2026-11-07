"""Forme : forme vs fatigue, VFC nocturne, sommeil, dernières sorties."""
from __future__ import annotations

from datetime import timedelta

from ...engine import vdot as V
from ...engine.seances import JOURS_COURTS, fmt_allure, fmt_date, fmt_duree, fmt_km
from .. import etat as E
from .. import theme as T
from ..commun import entete, html, nav


def afficher():
    ctx = E.contexte()
    auj = ctx.aujourd_hui
    acc = E.accent()
    entete("6 dernières semaines")
    nav("forme")

    ch = ctx.charge.tail(42)
    if not ch.empty:
        f, a, t = ch["forme"].iloc[-1], ch["fatigue"].iloc[-1], ch["fraicheur"].iloc[-1]
        html(f'''<div class="f-carte"><div class="f-ligne"><h2 class="f-titre" style="font-size:20px">Forme vs fatigue</h2>
          <span style="font-size:13px;font-weight:600;color:{T.BLEU}">Fraîcheur {t:+.0f}</span></div>
          {T.courbes_forme(list(ch["date"]), list(ch["forme"]), list(ch["fatigue"]), acc)}
          <div style="display:flex;gap:16px;font-size:13px">
          <span style="display:flex;align-items:center;gap:6px"><span style="width:14px;height:4px;border-radius:2px;background:{T.ENCRE}"></span>Forme {f:.0f}</span>
          <span style="display:flex;align-items:center;gap:6px"><span style="width:14px;height:4px;border-radius:2px;background:{acc}"></span>Fatigue {a:.0f}</span></div>
          <p class="f-sous" style="margin:8px 0 0;line-height:1.4">La forme monte lentement avec l'entraînement, la fatigue réagit vite.
          Fraîcheur positive = jambes reposées.</p></div>''')

    vfc = ctx.donnees.vfc
    if vfc is not None and not vfc.empty:
        dern = vfc[(vfc["date"] > auj - timedelta(days=30)) & (vfc["date"] <= auj)]
        m = ctx.meteo
        zone = (m.zone_basse, m.zone_haute)
        zone_txt = f"zone {m.zone_basse:.0f}–{m.zone_haute:.0f} ms" if m.zone_basse else "zone en calcul"
        html(f'''<div class="f-carte"><div class="f-ligne"><h2 class="f-titre" style="font-size:20px">VFC nocturne</h2>
          <span class="f-sous">{zone_txt}</span></div>
          {T.courbe_vfc(list(dern["nuit"]), zone, acc)}
          <p class="f-sous" style="margin:6px 0 0;line-height:1.4">{T.esc(m.titre)}. Les points orange sont les nuits sous ta zone.</p></div>''')

    som = ctx.donnees.sommeil
    if som is not None and not som.empty:
        jours = [auj - timedelta(days=k) for k in range(6, -1, -1)]
        par_jour = {r.date: r.heures for r in som.itertuples()}
        heures = [par_jour.get(j) for j in jours]
        connues = [h for h in heures if h]
        moy = fmt_duree(sum(connues) / len(connues) * 3600, court=True) if connues else "–"
        html(f'''<div class="f-carte"><div class="f-ligne"><h2 class="f-titre" style="font-size:20px">Sommeil</h2>
          <span class="f-sous">moy. {moy}</span></div>
          <div style="margin-top:8px">{T.barres_sommeil([JOURS_COURTS[j.weekday()] for j in jours], heures, acc)}</div></div>''')

    dist = ctx.profil.distance if ctx.profil.distance in V.DISTANCES else "10k"
    pred = V.temps_predit(ctx.vdot, V.DISTANCES[dist])
    html(f'''<div class="f-sombre"><div class="f-ligne"><span class="f-sous">Ton niveau aujourd'hui</span>
      <span class="f-titre" style="font-size:22px;color:{acc}">VDOT {ctx.vdot:.0f}</span></div>
      <p style="margin:8px 0 0;font-size:14px">Chrono prédit sur {V.NOMS_DISTANCES[dist].lower()} : <b>{fmt_duree(pred)}</b></p></div>''')

    acts = ctx.activites
    if acts is not None and not acts.empty:
        lignes = []
        for r in acts.sort_values("debut").tail(6).iloc[::-1].itertuples():
            if getattr(r, "sport", "course") == "velo":
                vitesse = f"{r.distance_km / (r.duree_s / 3600):.0f} km/h" if r.duree_s else "–"
                droite = f"{fmt_duree(r.duree_s, court=True)} · {vitesse}"
            else:
                allure = r.duree_s / r.distance_km if r.distance_km else None
                droite = f"{fmt_km(r.distance_km)} · {fmt_allure(allure)}"
            lignes.append(f'<li><span>{fmt_date(r.date)} · {T.esc(r.nom)}</span><span>{droite}</span></li>')
        html(f'<div class="f-carte"><h2 class="f-titre" style="font-size:20px">Dernières sorties</h2>'
             f'<ol class="f-etapes">{"".join(lignes)}</ol></div>')
