"""Morceaux d'interface partagés entre les écrans."""
from __future__ import annotations

from datetime import date

import streamlit as st

from ..engine import seances as S
from ..engine.seances import Seance, fmt_date, fmt_duree, fmt_km
from . import etat as E
from . import theme as T

TAGS = {
    "footing": ("Footing", T.VERT_FOND, T.VERT_TEXTE),
    "long": ("Sortie longue", T.VERT_FOND, T.VERT_TEXTE),
    "cotes": ("Côtes", T.ORANGE_FOND, T.ORANGE_TEXTE),
    "fartlek": ("Fartlek", T.ORANGE_FOND, T.ORANGE_TEXTE),
    "vma": ("Fractionné", T.ORANGE_FOND, T.ORANGE_TEXTE),
    "seuil": ("Seuil", T.BLEU_CLAIR, T.BLEU),
    "specifique": ("Allure course", T.BLEU_CLAIR, T.BLEU),
    "rappel": ("Rappel", T.BLEU_CLAIR, T.BLEU),
    "course": ("Jour J", T.ENCRE, T.BLANC),
    "renfo": ("Renfo", T.BLEU_CLAIR, T.BLEU),
    "velo_endurance": ("Vélo", "#E8E3FF", "#4B3AA8"),
    "velo_tempo": ("Vélo", "#E8E3FF", "#4B3AA8"),
    "velo_recup": ("Vélo", "#E8E3FF", "#4B3AA8"),
}
VELO_SVG = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4B3AA8" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="5.5" cy="16" r="3.5"/>'
            '<circle cx="18.5" cy="16" r="3.5"/><path d="M5.5 16 L10 8 h5 M10 8 l3.5 8 h5 M15 8 l-1.5-3 h-2"/></svg>')


def html(h: str):
    st.markdown(T.compact(h), unsafe_allow_html=True)


def entete(droite: str = ""):
    e = E.etat()
    col1, col2 = st.columns([3, 1.35], vertical_alignment="center")
    with col1:
        html(f'<div style="display:flex;align-items:center;gap:8px;padding-top:6px">{T.logo(E.accent())}'
             f'<span class="f-titre" style="font-size:21px">foulée</span>'
             f'<span class="f-sous" style="margin-left:6px">{T.esc(droite)}</span></div>')
    with col2:
        if e.get("onboarde") and st.button("Réglages", key="petit_reglages", icon=":material/tune:"):
            E.aller("reglages")


def _changer_page():
    choix = st.session_state.get("nav")
    if choix:
        st.session_state.page = E.PAGES_NAV[choix]


def nav(page: str):
    actuel = next((k for k, v in E.PAGES_NAV.items() if v == page), None)
    st.session_state.nav = actuel  # le contrôle suit toujours la page affichée
    st.segmented_control("Sections", list(E.PAGES_NAV), key="nav", label_visibility="collapsed",
                         on_change=_changer_page)


def note_coach(texte: str):
    html(f'<div class="f-bleu"><b>Le coach :</b> {T.esc(texte)}</div>')


def titre(texte: str, sous: str = "", taille: int = 34):
    sous_html = f'<p class="f-sous" style="margin:4px 0 0;font-size:15px">{T.esc(sous)}</p>' if sous else ""
    html(f'<div><h1 class="f-titre" style="font-size:{taille}px;margin:4px 0 0">{texte}</h1>{sous_html}</div>')


def tag_seance(s: Seance) -> str:
    nom, fond, coul = TAGS.get(s.genre, ("Séance", T.CREME_FONCE, T.ENCRE))
    return T.tag(nom, fond, coul)


def carte_seance(s: Seance, entete_txt: str = "Séance du jour", fait: dict | None = None):
    lignes = "".join(f"<li><span>{T.esc(a)}</span><span>{T.esc(b)}</span></li>" for a, b in S.resume_etapes(s))
    meta = (f"{fmt_duree(s.minutes * 60, court=True)}" if s.sport == "velo"
            else f"{fmt_duree(s.minutes * 60, court=True)} · ~{fmt_km(s.km)}")
    note = f'<p class="f-sous" style="margin:10px 0 0;line-height:1.4">{T.esc(s.note)}</p>' if s.note else ""
    allegee = T.tag("Allégée par le coach", T.BLEU_CLAIR, T.BLEU) if s.allegee else ""
    fait_html = ""
    if fait:
        fait_html = (f'<div style="margin-top:10px">{T.tag("Fait", T.VERT_FOND, T.VERT_TEXTE)} '
                     f'<span class="f-sous">{fmt_km(fait["distance_km"])} en {fmt_duree(fait["duree_s"])}</span></div>')
    html(f'''<div class="f-carte">
      <div class="f-ligne"><span>{tag_seance(s)} {allegee}</span><span class="f-sous">{meta}</span></div>
      <div class="f-titre" style="font-size:25px;margin-top:10px">{T.esc(s.titre.split("·", 1)[-1].strip() if "·" in s.titre else s.titre)}</div>
      <div class="f-sous" style="margin-top:2px">{T.esc(entete_txt)}</div>
      <ol class="f-etapes">{lignes}</ol>{note}{fait_html}</div>''')


def tuiles(valeurs: list[tuple[str, str, str]]):
    """[(libellé, valeur, couleur)]"""
    contenu = "".join(f'<div class="f-tuile"><div class="f-sous" style="font-size:12px">{T.esc(l)}</div>'
                      f'<div class="f-chiffre" style="color:{c}">{T.esc(v)}</div></div>' for l, v, c in valeurs)
    html(f'<div class="f-grille{len(valeurs)}">{contenu}</div>')


def carte_exo(exo, sous: str = ""):
    img = T.image_exo(exo.image)
    html(f'''<div class="f-exo"><img src="{img}" alt="{T.esc(exo.nom)}">
      <div style="flex:1;display:flex;flex-direction:column;gap:2px">
      <span class="f-exo-nom">{T.esc(exo.nom)}{sous}</span>
      <span class="f-sous" style="color:{T.GRIS_TEXTE};line-height:1.3">{T.esc(exo.phrase)}</span>
      <span style="font-size:13px;font-weight:600">{T.esc(exo.reps)}</span></div></div>''')


def jour_txt(j: date, aujourd_hui: date) -> str:
    if j == aujourd_hui:
        return f"{S.JOURS[j.weekday()]} · aujourd'hui"
    return f"{S.JOURS[j.weekday()]} {j.day} {S.MOIS[j.month - 1]}"


def boutons_velo(s: Seance, cle: str):
    from ..data.zwo import ecrire_zwo
    nom = f"foulee-{s.jour.isoformat()}-velo"
    st.download_button("Pour le home trainer (.zwo)", data=ecrire_zwo(s), file_name=f"{nom}.zwo",
                       mime="application/xml", key=f"zwo_{cle}", type="primary", icon=":material/pedal_bike:")
    if E.marque() != "polar":
        from ..data.fitfile import ecrire_seance
        st.download_button("Pour la montre ou le compteur (.fit)", data=ecrire_seance(s), file_name=f"{nom}.fit",
                           mime="application/octet-stream", key=f"fitv_{cle}", icon=":material/watch:")
    with st.expander("Comment l'utiliser ?"):
        st.markdown(
            "**Home trainer :** importe le fichier `.zwo` dans Zwift (*Entraînements › Personnalisés*, ou dossier "
            "`Documents/Zwift/Workouts`) ou dans une autre app de home trainer qui lit ce format. "
            "Les cibles sont en % de ta FTP : l'app les convertit en watts.\n\n"
            "**Dehors :** suis le repère cardio (FC) et le ressenti : en endurance, tu dois pouvoir discuter.\n\n"
            "Renseigne ta FTP dans les Réglages pour voir les watts ici. Pas de FTP ? Après un bon échauffement, "
            "roule 20 min le plus fort possible mais régulier : ta FTP ≈ 95 % de la puissance moyenne.")


def bouton_fit(s: Seance, cle: str):
    if E.marque() == "polar":
        with st.expander("Comment la mettre sur ma montre Polar ?"):
            st.markdown(
                "Polar ne permet pas aux apps perso d'envoyer une séance sur la montre. Sur **flow.polar.com** "
                "(ou l'app Polar Flow), crée un **objectif d'entraînement par phases**, recopie les étapes "
                "ci-dessus (durées et allures), puis synchronise ta montre.")
        return
    from ..data.fitfile import ecrire_seance
    nom = f"foulee-{s.jour.isoformat()}-{s.genre}.fit"
    st.download_button("Télécharger pour la montre", data=ecrire_seance(s), file_name=nom,
                       mime="application/octet-stream", key=f"fit_{cle}", type="primary",
                       icon=":material/watch:")
    with st.expander("Comment la mettre sur ma montre ?"):
        st.markdown(
            "**Depuis un ordinateur (fichier) :** branche ta montre en USB, puis copie le fichier "
            "téléchargé dans le dossier `GARMIN/NewFiles`. Débranche : la séance apparaît dans "
            "*Entraînement › Entraînements*.\n\n"
            "**Depuis ton téléphone :** dans l'app Garmin Connect › Entraînement › Entraînements › "
            "Créer, recopie les étapes ci-dessus (durées et allures), puis *Envoyer sur l'appareil*.\n\n"
            "Garmin ne permet pas encore aux apps perso d'envoyer une séance directement sur la montre.")
