"""Forme : forme vs fatigue, VFC nocturne, sommeil, dernières sorties."""
from __future__ import annotations

from datetime import timedelta

from ...engine import vdot as V
from ...engine.seances import JOURS_COURTS, fmt_allure, fmt_date, fmt_duree, fmt_km
from .. import etat as E
from .. import theme as T
from ..commun import entete, extras_html, html, nav


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

    _ma_montre(ctx)

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
            ex = extras_html(getattr(r, "extras", None))
            lignes.append(f'<li style="flex-direction:column;gap:0"><div class="f-ligne"><span>{fmt_date(r.date)} · {T.esc(r.nom)}</span>'
                          f'<span style="font-weight:600">{droite}</span></div>{ex}</li>')
        html(f'<div class="f-carte"><h2 class="f-titre" style="font-size:20px">Dernières sorties</h2>'
             f'<ol class="f-etapes" style="gap:12px">{"".join(lignes)}</ol></div>')


def _ma_montre(ctx):
    """Tout ce que ta montre mesure en plus : n'apparaît que ce qui existe dans tes données."""
    from ...data.metriques import QUOTIDIEN, formater
    q = ctx.donnees.quotidien
    if q is None or q.empty:
        return
    auj = ctx.aujourd_hui
    sept = q[(q["date"] > auj - timedelta(days=7)) & (q["date"] <= auj)]
    tuiles = []
    for k, (lib, _, _, agg) in QUOTIDIEN.items():
        if k not in q or not q[k].notna().any():
            continue
        dern = q[q["date"] <= auj][k].dropna()
        if dern.empty:
            continue
        s = sept[k].dropna() if k in sept else []
        if agg == "somme":
            principal, sous = formater(k, s.sum() if len(s) else None) + " / 7 j", "objectif OMS : 150 min / sem."
        else:
            principal = formater(k, dern.iloc[-1])
            sous = f"moy. 7 j : {formater(k, s.mean())}" if len(s) else ""
        tuiles.append(f'<div class="f-tuile" style="background:{T.CREME}"><div class="f-sous" style="font-size:12px">{T.esc(lib)}</div>'
                      f'<div class="f-chiffre">{T.esc(principal)}</div><div class="f-sous" style="font-size:11px">{T.esc(sous)}</div></div>')
    if tuiles:
        html(f'''<div class="f-carte"><div class="f-ligne"><h2 class="f-titre" style="font-size:20px">Ce que mesure ta montre</h2>
          <span class="f-sous">{len(tuiles)} mesures</span></div>
          <div class="f-grille2" style="margin-top:10px">{"".join(tuiles)}</div>
          <p class="f-sous" style="margin:8px 0 0;line-height:1.4">Seules les mesures que ta montre enregistre s'affichent ici.</p></div>''')
