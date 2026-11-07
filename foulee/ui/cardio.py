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


def flux(act: dict, seance=None, ctx=None) -> list[dict]:
    """FC tout au long de la sortie : téléchargée une fois depuis la montre, puis gardée."""
    ident = str(act["id"])
    cache = st.session_state.setdefault("flux_cache", {})
    if ident in cache:
        return cache[ident]
    ctx = ctx or E.contexte()
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


def genre_de(act: dict, seance=None) -> str:
    if seance is not None:
        return seance.genre
    if act.get("sport") == "velo":
        return "velo_endurance"
    return "long" if (act.get("duree_s") or 0) >= 75 * 60 else "footing"


def analyse(act: dict, seance=None, garder: bool = True, ctx=None, sauver: bool = True):
    """Analyse la FC de la sortie et la garde : le coach s'en sert pour ajuster le plan."""
    ctx = ctx or E.contexte()
    genre = genre_de(act, seance)
    an = CA.analyser(flux(act, seance, ctx), ctx.profil.fc_max or 190, ctx.donnees.fc_repos(), genre)
    if an is not None and garder:
        e = E.etat()
        cardio = e.setdefault("cardio", {})
        ident = str(act["id"])
        jour = act["date"].isoformat() if hasattr(act["date"], "isoformat") else str(act["date"])
        if ident not in cardio:
            cardio[ident] = {"jour": jour, "genre": genre, **an.resume()}
            if sauver:
                E.sauver()
                E.invalider()
    return an


def analyser_tout(acts: list[dict], liens: dict, plan) -> int:
    """Analyse d'un coup les sorties pas encore analysées."""
    e = E.etat()
    faites = set((e.get("cardio") or {}).keys())
    a_faire = [a for a in acts if str(a["id"]) not in faites]
    par_id = {str(a["id"]): s for s in plan.seances() if (a := liens.get(s.ident)) is not None}
    n = 0
    ctx = E.contexte()
    barre = st.progress(0.0, text="Analyse de ta FC…")
    for k, act in enumerate(a_faire, 1):
        if analyse(act, par_id.get(str(act["id"])), ctx=ctx, sauver=False) is not None:
            n += 1
        barre.progress(k / len(a_faire), text=f"Analyse de ta FC… {k}/{len(a_faire)}")
    E.sauver()
    E.invalider()
    return n


def cible_txt(s) -> str:
    """« 133–146 bpm » + conseil, pour la carte d'une séance."""
    ctx = E.contexte()
    b = CA.bornes(ctx.profil.fc_max or 190, ctx.donnees.fc_repos())
    c = CA.cible(s.genre, b)
    return c[2] if c else ""


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
