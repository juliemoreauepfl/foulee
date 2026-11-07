"""Récupère la FC seconde par seconde d'une sortie et affiche son analyse."""
from __future__ import annotations

import streamlit as st

from ..data import demo
from ..data.fitfile import lire_flux
from ..engine import cardio as CA
from . import etat as E
from . import theme as T
from .commun import html

TONS = {"ok": (T.VERT_FOND, T.VERT_TEXTE), "attention": (T.ORANGE_FOND, T.ORANGE_TEXTE), "info": (T.BLEU_CLAIR, T.BLEU_TEXTE)}


def flux(act: dict, seance=None) -> list[dict]:
    """FC tout au long de la sortie : téléchargée une fois depuis la montre, puis gardée."""
    ident = str(act["id"])
    cache = st.session_state.setdefault("flux_cache", {})
    if ident in cache:
        return cache[ident]
    ctx = E.contexte()
    if E.etat().get("mode") == "demo" or ident.startswith("demo"):
        res = demo.flux_simule(seance, act, ctx.donnees.fc_repos(), ctx.profil.fc_max or 190)
    else:
        res = []
        try:
            res = E.stockage().lire(f"flux_{ident}", None) or []
        except Exception:
            res = []
        if not res and E.connecte() and not ident.startswith(("fichier-", "manuel-")):
            try:
                with st.spinner("Je récupère ta FC pendant la sortie…"):
                    contenu = E.client().fichier_activite(act["id"])
                res = lire_flux(contenu) if contenu else []
                if res:
                    E.stockage().ecrire(f"flux_{ident}", res)
            except Exception:
                res = []
    cache[ident] = res
    return res


def analyse(act: dict, seance=None):
    ctx = E.contexte()
    genre = seance.genre if seance is not None else ("velo_endurance" if act.get("sport") == "velo" else "footing")
    return CA.analyser(flux(act, seance), ctx.profil.fc_max or 190, ctx.donnees.fc_repos(), genre)


def carte(an) -> None:
    if an is None:
        html('<div class="f-carte"><h2 class="f-titre" style="font-size:20px">Ton cœur pendant la sortie</h2>'
             '<p class="f-sous" style="margin:6px 0 0;line-height:1.4">Pas de fréquence cardiaque détaillée pour cette sortie '
             '(saisie à la main, fichier sans capteur, ou montre pas encore synchronisée).</p></div>')
        return
    b = an.bornes
    legende = "".join(
        f'<li><span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:{T.COULEURS_ZONES[k]};'
        f'margin-right:6px"></span>Z{k + 1} {CA.NOMS_ZONES[k]} <span class="f-sous">{b[k]}–{b[k + 1]}</span></span>'
        f'<span>{CA.fmt_min(an.secondes[k])} · {an.pct[k]} %</span></li>' for k in range(5))
    derive = f" · dérive {round(an.derive) or 0:+d} %".replace("+0", "0") if an.derive is not None else ""
    msgs = "".join(f'<div style="background:{TONS[t][0]};color:{TONS[t][1]};border-radius:16px;padding:10px 13px;'
                   f'font-size:13.5px;line-height:1.4;margin-top:8px">{T.esc(x)}</div>' for t, x in an.messages)
    html(f'''<div class="f-carte"><div class="f-ligne"><h2 class="f-titre" style="font-size:20px">Ton cœur pendant la sortie</h2>
      <span class="f-sous">moy. {an.fc_moy} · pic {an.fc_pic}{derive}</span></div>
      <div style="margin-top:8px">{T.courbe_fc(an.points, b)}</div>
      <div style="margin-top:8px">{T.barre_zones(an.pct)}</div>
      <ol class="f-etapes" style="font-size:13px">{legende}</ol>{msgs}</div>''')
