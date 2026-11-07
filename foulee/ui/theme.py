"""Le look de Foulée : CSS, petits composants HTML et graphiques SVG faits main."""
from __future__ import annotations

import base64
import html as _html
from functools import lru_cache
from pathlib import Path

ENCRE, CREME, CREME_FONCE, BLANC = "#17171C", "#F5F1EA", "#EAE4DA", "#FFFFFF"
GRIS, GRIS_TEXTE = "#5E5B57", "#4A4743"
ACCENT = "#FF6B2C"
BLEU, BLEU_CLAIR, BLEU_TEXTE = "#24399E", "#DCE4FF", "#1C2B78"
VERT_FOND, VERT_TEXTE = "#E7F4EA", "#1E6B35"
ORANGE_FOND, ORANGE_TEXTE = "#FFE7DC", "#9A3412"

ASSETS = Path(__file__).resolve().parents[2] / "assets"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Inter:wght@400;500;600&display=swap');
:root {{ --accent: {ACCENT}; }}
html, body, .stApp, [data-testid="stAppViewContainer"] {{ background: {CREME} !important; color: {ENCRE}; }}
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button {{ font-family: Inter, sans-serif; }}
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{ display: none !important; }}
.block-container {{ max-width: 460px !important; padding: 1rem 1.1rem 4rem !important; }}
[data-testid="stVerticalBlock"] {{ gap: 0.75rem; }}
h1, h2, h3, .f-titre {{ font-family: 'Bricolage Grotesque', sans-serif !important; letter-spacing: -0.03em; color: {ENCRE}; }}

/* Boutons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  width: 100%; min-height: 50px; border-radius: 999px; font-weight: 600; font-size: 15px;
  border: 1.5px solid {ENCRE}; background: transparent; color: {ENCRE}; transition: transform .08s ease; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: {BLEU}; color: {BLEU}; }}
.stButton > button:active {{ transform: scale(.98); }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"], .stFormSubmitButton > button {{
  background: {ENCRE}; color: {BLANC}; border: none; }}
.stButton > button[kind="primary"]:hover {{ background: #2A2A33; color: {BLANC}; }}
[class*="st-key-accent"] button {{ background: var(--accent) !important; color: {ENCRE} !important; border: none !important;
  font-family: 'Bricolage Grotesque', sans-serif !important; font-size: 19px !important; font-weight: 800 !important; min-height: 56px; }}
[class*="st-key-petit"] button {{ min-height: 40px; font-size: 13px; padding: 0 12px; }}
[class*="st-key-lien"] button {{ border: none; min-height: 40px; color: {BLEU}; justify-content: flex-start; padding-left: 0; text-decoration: underline; }}

/* Contrôles segmentés et pastilles */
[data-testid="stButtonGroup"] {{ width: 100%; }}
[data-testid="stButtonGroup"] > div {{ display: flex; flex-wrap: wrap; gap: 6px; width: 100%; }}
button[data-testid^="stBaseButton-segmented_control"], button[data-testid^="stBaseButton-pills"] {{
  border-radius: 999px !important; min-height: 42px; border: 1.5px solid #E2DBD0 !important; background: {BLANC} !important;
  color: {ENCRE} !important; font-weight: 600; flex: 1 1 auto; }}
button[data-testid="stBaseButton-segmented_controlActive"], button[data-testid="stBaseButton-pillsActive"] {{
  background: {ENCRE} !important; color: {BLANC} !important; border-color: {ENCRE} !important; }}
.st-key-nav [data-testid="stButtonGroup"] > div {{ background: {CREME_FONCE}; padding: 4px; border-radius: 999px; flex-wrap: nowrap; gap: 4px; }}
.st-key-nav button[data-testid^="stBaseButton-segmented_control"] {{ border: none !important; background: transparent !important; min-height: 38px; font-size: 13px; padding: 0 4px; }}
.st-key-nav button[data-testid="stBaseButton-segmented_controlActive"] {{ background: {ENCRE} !important; color: {BLANC} !important; }}

/* Champs */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea, [data-baseweb="select"] > div {{
  border-radius: 16px !important; background: {BLANC} !important; border: 1.5px solid #E2DBD0 !important; }}
.stTextInput label, .stDateInput label, .stTextArea label, .stNumberInput label, .stSelectbox label,
[data-testid="stWidgetLabel"] p {{ font-weight: 600 !important; font-size: 13px !important; color: {ENCRE} !important; }}
[data-testid="stExpander"] {{ background: {BLANC}; border-radius: 20px; border: none; }}
[data-testid="stExpander"] summary {{ font-weight: 600; }}
[data-testid="stFileUploaderDropzone"] {{ border-radius: 20px; background: {BLANC}; }}

/* Cartes maison */
.f-carte {{ background: {BLANC}; border-radius: 26px; padding: 16px 18px; }}
.f-sombre {{ background: {ENCRE}; color: {BLANC}; border-radius: 26px; padding: 16px 18px; }}
.f-sombre .f-sous {{ color: #CFCBC4; }}
.f-sombre .f-titre, .f-sombre .f-chiffre, .f-sombre b {{ color: {BLANC}; }}
.f-accent {{ background: var(--accent); border-radius: 28px; padding: 16px 18px; }}
.f-bleu {{ background: {BLEU_CLAIR}; color: {BLEU_TEXTE}; border-radius: 22px; padding: 13px 16px; font-size: 14px; line-height: 1.45; }}
.f-titre {{ font-weight: 800; margin: 0; line-height: 1.02; }}
.f-sous {{ color: {GRIS}; font-size: 13px; }}
.f-tag {{ display: inline-block; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; }}
.f-ligne {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
.f-grille3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }}
.f-grille2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
.f-tuile {{ background: {BLANC}; border-radius: 20px; padding: 11px 13px; }}
.f-chiffre {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 21px; line-height: 1.15; }}
.f-etapes {{ list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 7px; font-size: 14px; }}
.f-etapes li {{ display: flex; justify-content: space-between; gap: 12px; }}
.f-etapes li span:last-child {{ font-weight: 600; white-space: nowrap; }}
.f-barre {{ height: 10px; border-radius: 999px; background: #3A3A42; overflow: hidden; }}
.f-barre > div {{ height: 10px; border-radius: 999px; background: var(--accent); }}
.f-exo {{ background: {BLANC}; border-radius: 22px; padding: 8px 14px 8px 8px; display: flex; gap: 12px; align-items: center; }}
.f-exo img {{ width: 72px; height: 72px; border-radius: 16px; flex-shrink: 0; }}
.f-exo-nom {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 17px; line-height: 1.15; }}
.f-jours {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; text-align: center; }}
.f-pastille {{ width: 36px; height: 36px; border-radius: 999px; display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; margin: 4px auto 0; box-sizing: border-box; }}
/* Streamlit donne une marge négative aux blocs de texte : nos cartes se chevauchaient */
.stMarkdown, [data-testid="stMarkdown"], [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
[data-testid="stMarkdownContainer"] > div:last-child, [data-testid="stMarkdownContainer"] > p:last-child {{ margin-bottom: 0 !important; }}
.f-bloc {{ display: flow-root; padding-bottom: 1px; }}
/* Sur téléphone, Streamlit empile les colonnes : on garde nos boutons côte à côte */
[data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 8px !important; }}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"], [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
  min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }}
@media (max-width: 380px) {{ .block-container {{ padding: .6rem .7rem 3rem !important; }} }}
</style>
"""


def css(accent: str = ACCENT) -> str:
    return CSS.replace(f"--accent: {ACCENT}", f"--accent: {accent}")


def esc(t) -> str:
    return _html.escape("" if t is None else str(t))


def compact(h: str) -> str:
    """Le markdown de Streamlit casse le HTML indenté ou avec lignes vides."""
    return " ".join(l.strip() for l in h.splitlines() if l.strip())


def tag(texte: str, fond: str, couleur: str) -> str:
    return f'<span class="f-tag" style="background:{fond};color:{couleur}">{esc(texte)}</span>'


@lru_cache(maxsize=64)
def image_exo(nom_fichier: str) -> str:
    p = ASSETS / "exos" / nom_fichier
    if not p.exists():
        return ""
    return "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()


def logo(accent: str = ACCENT, taille: int = 28) -> str:
    return (f'<svg width="{taille}" height="{taille}" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="14" fill="{accent}"/>'
            f'<path d="M8 18 C11 9, 15 9, 20 10" stroke="{ENCRE}" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
            f'<circle cx="20" cy="10" r="2.2" fill="{ENCRE}"/></svg>')


# ------------------------------------------------------------ météo intérieure
def meteo_svg(etat: str) -> str:
    rayons = ('<g stroke="#17171C" stroke-width="3" stroke-linecap="round">'
              '<line x1="36" y1="3" x2="36" y2="11"/><line x1="36" y1="61" x2="36" y2="69"/>'
              '<line x1="3" y1="36" x2="11" y2="36"/><line x1="61" y1="36" x2="69" y2="36"/>'
              '<line x1="12.7" y1="12.7" x2="18.4" y2="18.4"/><line x1="53.6" y1="53.6" x2="59.3" y2="59.3"/>'
              '<line x1="12.7" y1="59.3" x2="18.4" y2="53.6"/><line x1="53.6" y1="18.4" x2="59.3" y2="12.7"/></g>')
    soleil = '<circle cx="36" cy="36" r="19" fill="#FFF6E8" stroke="#17171C" stroke-width="3"/>'
    yeux = '<circle cx="30" cy="33" r="2.2" fill="#17171C"/><circle cx="42" cy="33" r="2.2" fill="#17171C"/>'
    sourire = '<path d="M29 40 Q36 46 43 40" stroke="#17171C" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
    neutre = '<path d="M30 42 L42 42" stroke="#17171C" stroke-width="2.6" stroke-linecap="round"/>'
    nuage = ('<path d="M18 58 a12 12 0 0 1 2-24 a16 16 0 0 1 30-4 a12 12 0 0 1 4 28 Z" fill="#FFFFFF" '
             'stroke="#17171C" stroke-width="3" stroke-linejoin="round"/>')
    yeux_n = '<circle cx="30" cy="45" r="2.2" fill="#17171C"/><circle cx="42" cy="45" r="2.2" fill="#17171C"/>'
    bouche_n = '<path d="M31 52 Q36 49 41 52" stroke="#17171C" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
    eclair = '<path d="M38 60 L32 70 L38 70 L34 80" stroke="#17171C" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    if etat == "soleil":
        corps = rayons + soleil + yeux + sourire
    elif etat == "eclaircies":
        corps = ('<g transform="translate(14,-8) scale(.8)">' + rayons + soleil + '</g>'
                 '<g transform="translate(-6,4)">' + nuage + yeux_n + '<path d="M31 51 Q36 54 41 51" stroke="#17171C" '
                 'stroke-width="2.4" fill="none" stroke-linecap="round"/></g>')
    elif etat in ("nuages", "voile"):
        corps = nuage + yeux_n + (bouche_n if etat == "nuages" else '<path d="M31 51 L41 51" stroke="#17171C" stroke-width="2.4" stroke-linecap="round"/>')
    elif etat == "orage":
        corps = nuage + yeux_n + bouche_n + eclair
    else:
        corps = soleil + yeux + neutre
    return f'<svg width="76" height="76" viewBox="0 0 72 84" role="img" aria-label="Météo intérieure">{corps}</svg>'


def visage_svg(niveau: int, taille: int = 64) -> str:
    bouches = {1: "M11 21 Q17 26 23 21", 2: "M11 21 Q17 24 23 21", 3: "M11 22 L23 22",
               4: "M11 23 Q17 20 23 23", 5: "M12 24 Q17 18 22 24"}
    fonds = {1: VERT_FOND, 2: VERT_FOND, 3: "#FFF1C7", 4: ORANGE_FOND, 5: "#FFD0BD"}
    sueur = '<path d="M27 8 q2 4 0 6 q-2 -2 0 -6" fill="#24399E"/>' if niveau >= 4 else ""
    return (f'<svg width="{taille}" height="{taille}" viewBox="0 0 34 34" aria-hidden="true">'
            f'<circle cx="17" cy="17" r="15" fill="{fonds[niveau]}" stroke="#17171C" stroke-width="2"/>'
            f'<circle cx="12" cy="14" r="1.8" fill="#17171C"/><circle cx="22" cy="14" r="1.8" fill="#17171C"/>'
            f'<path d="{bouches[niveau]}" stroke="#17171C" stroke-width="2" fill="none" stroke-linecap="round"/>{sueur}</svg>')


# ------------------------------------------------------------ graphiques
def _chemin(points):
    return " ".join(("M" if i == 0 else "L") + f"{x:.1f} {y:.1f}" for i, (x, y) in enumerate(points))


def courbes_forme(dates, forme, fatigue, accent=ACCENT, w=320, h=120) -> str:
    vals = [v for v in list(forme) + list(fatigue) if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals) * 0.9, max(vals) * 1.05 + 1e-6
    n = len(forme)
    sx = lambda i: 4 + i * (w - 8) / max(n - 1, 1)
    sy = lambda v: h - 8 - (v - lo) / (hi - lo) * (h - 16)
    pf = _chemin([(sx(i), sy(v)) for i, v in enumerate(forme)])
    pa = _chemin([(sx(i), sy(v)) for i, v in enumerate(fatigue)])
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Courbes de forme et de fatigue">'
            f'<line x1="0" y1="{h - 3}" x2="{w}" y2="{h - 3}" stroke="{CREME_FONCE}"/>'
            f'<path d="{pf}" fill="none" stroke="{ENCRE}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{pa}" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def courbe_vfc(valeurs, zone, accent=ACCENT, w=320, h=110) -> str:
    vals = [v for v in valeurs if v is not None]
    if len(vals) < 2:
        return ""
    lo_z, hi_z = zone if zone and zone[0] else (min(vals), max(vals))
    lo = min(min(vals), lo_z) - 4
    hi = max(max(vals), hi_z) + 4
    n = len(valeurs)
    sx = lambda i: 6 + i * (w - 12) / max(n - 1, 1)
    sy = lambda v: h - 6 - (v - lo) / (hi - lo) * (h - 12)
    pts = [(sx(i), sy(v)) for i, v in enumerate(valeurs) if v is not None]
    bande = (f'<rect x="0" y="{sy(hi_z):.1f}" width="{w}" height="{sy(lo_z) - sy(hi_z):.1f}" rx="8" fill="{BLEU_CLAIR}"/>'
             if zone and zone[0] else "")
    creux = "".join(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="4.5" fill="{accent}" stroke="{ENCRE}" stroke-width="1.5"/>'
                    for i, v in enumerate(valeurs) if v is not None and zone and zone[0] and v < lo_z)
    x, y = pts[-1]
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="VFC nocturne et zone habituelle">{bande}'
            f'<path d="{_chemin(pts)}" fill="none" stroke="{BLEU}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
            f'{creux}<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{BLEU}"/></svg>')


def barres_sommeil(jours, heures, accent=ACCENT) -> str:
    cols = []
    for j, hres in zip(jours, heures):
        hauteur = 8 if hres is None else max(8, min(88, (hres - 4.5) * 22))
        couleur = CREME_FONCE if hres is None else (accent if hres < 6.5 else ENCRE)
        cols.append(f'<div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:4px;height:110px">'
                    f'<div style="width:100%;height:{hauteur:.0f}px;border-radius:10px;background:{couleur}"></div>'
                    f'<span class="f-sous" style="font-size:12px">{esc(j)}</span></div>')
    return f'<div style="display:grid;grid-template-columns:repeat({len(cols)},minmax(0,1fr));gap:8px">{"".join(cols)}</div>'


COULEURS_ZONES = ["#D9D2C7", "#9DB0F0", "#7CC59A", "#FFB37A", "#FF6B6B"]


def courbe_fc(points, b, w=340, h=150) -> str:
    """Courbe de FC sur fond de zones. points : [(t s, fc)], b : bornes Z1..Z5 + FC max."""
    if len(points) < 2:
        return ""
    fcs = [f for _, f in points]
    lo = min(min(fcs), b[0]) - 5
    hi = max(max(fcs), b[4]) + 5
    t_max = points[-1][0] or 1
    g = 30
    sx = lambda t: g + t / t_max * (w - g - 4)
    sy = lambda f: h - 18 - (f - lo) / (hi - lo) * (h - 26)
    bandes = []
    limites = [lo] + list(b[1:5]) + [hi]
    for k in range(5):
        y1, y2 = sy(min(limites[k + 1], hi)), sy(max(limites[k], lo))
        if y2 > y1:
            bandes.append(f'<rect x="{g}" y="{y1:.1f}" width="{w - g - 4}" height="{y2 - y1:.1f}" fill="{COULEURS_ZONES[k]}" opacity=".35"/>'
                          f'<text x="{g - 4}" y="{(y1 + y2) / 2 + 4:.1f}" text-anchor="end" font-size="10" fill="{GRIS}">Z{k + 1}</text>')
    chemin = _chemin([(sx(t), sy(f)) for t, f in points])
    graduations = "".join(
        f'<text x="{sx(m * 60):.1f}" y="{h - 3}" text-anchor="middle" font-size="10" fill="{GRIS}">{m}\u2032</text>'
        for m in range(0, int(t_max // 60) + 1, max(10, int(t_max // 60 // 5) // 10 * 10 or 10)))
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Fréquence cardiaque pendant la sortie">'
            f'{"".join(bandes)}<path d="{chemin}" fill="none" stroke="{ENCRE}" stroke-width="2" stroke-linejoin="round"/>'
            f'{graduations}</svg>')


def barre_zones(pct) -> str:
    morceaux = "".join(f'<div style="width:{p}%;background:{c}" title="Z{k + 1} {p} %"></div>'
                       for k, (p, c) in enumerate(zip(pct, COULEURS_ZONES)) if p > 0)
    return f'<div style="display:flex;height:14px;border-radius:999px;overflow:hidden;gap:2px">{morceaux}</div>'


def fete(titre: str, sous: str, accent: str = ACCENT) -> str:
    """Petite fête plein écran : confettis + coureur qui saute, disparaît toute seule (CSS pur)."""
    import random as _r
    rng = _r.Random(titre)
    couleurs = [accent, BLEU, "#7CC59A", "#FFD23F", "#FF6B6B", ENCRE]
    confettis = "".join(
        f'<i style="left:{rng.uniform(0, 100):.0f}%;background:{rng.choice(couleurs)};'
        f'animation-delay:{rng.uniform(0, 1.2):.2f}s;animation-duration:{rng.uniform(2.2, 3.6):.2f}s;'
        f'width:{rng.choice([6, 8, 10])}px;height:{rng.choice([10, 14, 6])}px;transform:rotate({rng.randint(0, 90)}deg)"></i>'
        for _ in range(70))
    coureur = (f'<svg class="f-fete-coureur" width="120" height="120" viewBox="0 0 120 120" aria-hidden="true">'
               f'<circle cx="60" cy="60" r="56" fill="{accent}"/>'
               f'<circle cx="68" cy="30" r="9" fill="{ENCRE}"/>'
               f'<path d="M64 42 L54 66 L70 76 L62 98 M54 66 L40 84 M60 50 L80 58 L88 48 M60 50 L42 46 L34 56" '
               f'stroke="{ENCRE}" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
               f'<path d="M20 20 l4 8 l8 4 l-8 4 l-4 8 l-4 -8 l-8 -4 l8 -4z" fill="{BLANC}"/>'
               f'<path d="M98 82 l3 6 l6 3 l-6 3 l-3 6 l-3 -6 l-6 -3 l6 -3z" fill="{BLANC}"/></svg>')
    return f"""<style>
.f-fete {{ position: fixed; inset: 0; z-index: 99999; pointer-events: none; overflow: hidden;
  animation: f-fete-fin 5.2s ease forwards; }}
.f-fete i {{ position: absolute; top: -20px; border-radius: 2px; animation-name: f-tombe; animation-timing-function: linear;
  animation-iteration-count: 1; animation-fill-mode: forwards; }}
.f-fete-carte {{ position: absolute; left: 50%; top: 38%; transform: translate(-50%, -50%); text-align: center;
  background: {BLANC}; border-radius: 32px; padding: 22px 26px; box-shadow: 0 20px 60px rgba(0,0,0,.18);
  width: min(320px, 82vw); animation: f-pop .6s cubic-bezier(.2,1.6,.4,1) both; }}
.f-fete-coureur {{ animation: f-saut .5s ease-in-out .5s 6 alternate; }}
@keyframes f-tombe {{ to {{ top: 105vh; transform: rotate(720deg) translateX(40px); }} }}
@keyframes f-pop {{ from {{ transform: translate(-50%, -50%) scale(.3); opacity: 0; }} }}
@keyframes f-saut {{ to {{ transform: translateY(-16px) rotate(-6deg); }} }}
@keyframes f-fete-fin {{ 0%, 85% {{ opacity: 1; }} 100% {{ opacity: 0; visibility: hidden; }} }}
@media (prefers-reduced-motion: reduce) {{ .f-fete i, .f-fete-coureur {{ animation: none; display: none; }} }}
</style>
<div class="f-fete" role="status" aria-live="polite">{confettis}
<div class="f-fete-carte">{coureur}
<div class="f-titre" style="font-size:26px;margin-top:10px">{esc(titre)}</div>
<p class="f-sous" style="margin:6px 0 0;font-size:14px;line-height:1.4">{esc(sous)}</p></div></div>"""


COULEURS_PHASES = {"base": "#D9D2C7", "dev": "#9DB0F0", "spe": None, "aff": "#7CC59A"}


def graphe_plan(semaines: list[dict], accent: str = ACCENT, w: int = 340, h: int = 150) -> str:
    """Charge prévue par semaine (barres colorées par phase), charge réalisée (barre noire
    à l'intérieur), semaine en cours entourée, drapeau le jour J."""
    if not semaines:
        return ""
    n = len(semaines)
    haut = max(max(s["prevue"] for s in semaines), max((s["faite"] or 0) for s in semaines), 1) * 1.12
    marge_b = 18
    pas = (w - 4) / n
    larg = max(3.0, pas * 0.72)
    sy = lambda v: (h - marge_b) * (1 - v / haut)
    barres = []
    for i, s in enumerate(semaines):
        x = 2 + i * pas + (pas - larg) / 2
        coul = COULEURS_PHASES.get(s["phase"]) or accent
        y = sy(s["prevue"])
        barres.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{larg:.1f}" height="{h - marge_b - y:.1f}" rx="{min(4, larg / 2):.1f}" fill="{coul}"/>')
        if s["faite"]:
            yf = sy(s["faite"])
            lf = larg * 0.5
            barres.append(f'<rect x="{x + (larg - lf) / 2:.1f}" y="{yf:.1f}" width="{lf:.1f}" height="{h - marge_b - yf:.1f}" '
                          f'rx="{min(3, lf / 2):.1f}" fill="{ENCRE}"/>')
        if s["courante"]:
            barres.append(f'<rect x="{x - 2:.1f}" y="{y - 3:.1f}" width="{larg + 4:.1f}" height="{h - marge_b - y + 3:.1f}" '
                          f'rx="5" fill="none" stroke="{ENCRE}" stroke-width="2"/>'
                          f'<text x="{x + larg / 2:.1f}" y="{h - 4}" font-size="10" text-anchor="middle" fill="{ENCRE}" '
                          f'font-family="Inter, sans-serif" font-weight="600">auj.</text>')
        if s.get("jour_j"):
            xf = x + larg / 2
            barres.append(f'<path d="M{xf:.1f} {y - 4:.1f} V{y - 22:.1f} l9 4 l-9 4" stroke="{ENCRE}" stroke-width="2" '
                          f'fill="{accent}" stroke-linejoin="round"/>'
                          f'<text x="{xf:.1f}" y="{h - 4}" font-size="10" text-anchor="middle" fill="{ENCRE}" '
                          f'font-family="Inter, sans-serif" font-weight="600">J</text>')
    return (f'<svg viewBox="0 -24 {w} {h + 24}" width="100%" role="img" aria-label="Charge d\'entraînement prévue et '
            f'réalisée par semaine jusqu\'à l\'objectif">{"".join(barres)}</svg>')


def legende_phases(phases: list[str], accent: str = ACCENT) -> str:
    noms = {"base": "Base", "dev": "Développement", "spe": "Spécifique", "aff": "Affûtage"}
    items = [f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px">'
             f'<span style="width:12px;height:12px;border-radius:4px;background:{COULEURS_PHASES.get(p) or accent}"></span>'
             f'{noms[p]}</span>' for p in dict.fromkeys(phases)]
    items.append(f'<span style="display:inline-flex;align-items:center;gap:5px"><span style="width:6px;height:12px;'
                 f'border-radius:3px;background:{ENCRE}"></span>Réalisé</span>')
    return f'<div class="f-sous" style="font-size:12px;line-height:2">{"".join(items)}</div>'
