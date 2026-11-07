"""Premier lancement : clé Garmin → import → « voilà ce que j'ai compris de toi »."""
from __future__ import annotations

from datetime import date

import streamlit as st

from ... import coach
from ...data.fichiers import importer
from ...engine.seances import MOIS, fmt_allure
from .. import etat as E
from .. import theme as T
from ..commun import entete, html, titre, tuiles


def _points(etape: int):
    pts = "".join(f'<span style="display:block;height:8px;border-radius:999px;width:{22 if i == etape else 8}px;'
                  f'background:{T.ENCRE if i <= etape else "#D6CEC2"}"></span>' for i in (1, 2, 3))
    html(f'<div style="display:flex;gap:6px;justify-content:flex-end" role="img" aria-label="Étape {etape} sur 3">{pts}</div>')


def afficher():
    e = E.etat()
    etape = st.session_state.get("ob_etape", 1)
    entete()
    _points(etape)
    if etape == 1:
        _etape_cle(e)
    elif etape == 2:
        _etape_import(e)
    else:
        _etape_portrait(e)


def _etape_cle(e):
    titre("On fait<br>connaissance ?", "Je lis tes 6 derniers mois pour partir de là où tu en es, pas d'un plan tout fait.", 40)
    prenom = st.text_input("Ton prénom", value=e.get("prenom", ""), placeholder="Julie")
    montre = st.segmented_control("Ta montre", ["Garmin", "Polar"],
                                  default="Polar" if e.get("mode") == "polar" else "Garmin", key="choix_montre")
    if montre == "Polar":
        _polar(e, prenom)
    else:
        _garmin(e, prenom)

    with st.expander("Autre montre ? Importer des fichiers .FIT / .GPX"):
        fichiers = st.file_uploader("Tes sorties", type=["fit", "gpx", "zip"], accept_multiple_files=True,
                                    label_visibility="collapsed")
        if fichiers and st.button("Importer ces fichiers", key="importer", type="primary"):
            n = _importer(e, fichiers)
            e["prenom"] = prenom.strip()
            e["mode"] = "fichiers"
            E.sauver()
            st.success(f"{n} sortie(s) importée(s).")
            E.aller("bienvenue", ob_etape=3)

    if st.button("Essayer avec des données de démo", key="lien_demo"):
        e["prenom"] = prenom.strip() or "Julie"
        e["mode"] = "demo"
        E.sauver()
        E.aller("bienvenue", ob_etape=2)


def _polar(e, prenom):
    from ...data.polar import url_autorisation
    sec = E.secrets()
    if E.jeton_polar().get("access_token"):
        html('<div class="f-bleu">Ton compte Polar est connecté. Polar ne garde que tes 30 derniers jours : '
             'je pars de là, et j\'accumule ton historique au fil des semaines.</div>')
        if st.button("Lire mon historique", key="accent_lire_polar"):
            e["prenom"] = prenom.strip()
            e["mode"] = "polar"
            E.sauver()
            E.aller("bienvenue", ob_etape=2)
        return
    if not (sec.get("POLAR_CLIENT_ID") and sec.get("POLAR_CLIENT_SECRET")):
        html('<div class="f-bleu">Pour Polar, il faut d\'abord créer ton accès gratuit (5 min) : '
             'le guide explique tout, section « Polar ».</div>')
        with st.expander("En bref"):
            st.markdown(
                "1. Sur **admin.polaraccesslink.com**, connecte-toi avec ton compte Polar Flow et crée un client.\n"
                f"2. Lien de retour (*redirect URL*) : `{_url_app()}`\n"
                "3. Copie le *Client ID* et le *Client secret* dans les secrets de l'app : "
                "`POLAR_CLIENT_ID`, `POLAR_CLIENT_SECRET` (et `APP_URL` si l'app est en ligne).")
        return
    if "polar_url" not in st.session_state:
        url, etat_oauth = url_autorisation(sec["POLAR_CLIENT_ID"], _url_app())
        st.session_state.polar_url = url
        try:
            E.stockage().ecrire("polar_etat", {"etat": etat_oauth, "prenom": prenom.strip()})
        except Exception:
            pass
    e["prenom"] = prenom.strip()
    st.link_button("Connecter mon compte Polar", st.session_state.polar_url, type="primary")
    html('<p class="f-sous" style="margin:-4px 0 0">Polar te demande ton accord, puis te renvoie ici.</p>')


def _url_app() -> str:
    return E.secrets().get("APP_URL", "http://localhost:8501").rstrip("/") + "/"


def _garmin(e, prenom):
    a_secret = bool(E.secrets().get("GARMIN_API_KEY"))
    if a_secret:
        html('<div class="f-bleu">Ta clé Garmin est déjà rangée dans les secrets de l\'app. Parfait.</div>')
    else:
        st.text_input("Ta clé Garmin personnelle", type="password", key="cle_saisie",
                      help="Garmin Connect (site web) › Paramètres › Personal API Token › Créer une clé.")
        html('<p class="f-sous" style="margin:-4px 0 0">Sur ton téléphone, mieux vaut la mettre dans les secrets '
             'Streamlit (voir le guide). Ici, elle reste le temps de ta visite.</p>')

    if st.button("Lire mon historique", key="accent_lire", disabled=not (a_secret or st.session_state.get("cle_saisie"))):
        e["prenom"] = prenom.strip()
        e["mode"] = "garmin"
        if not a_secret and isinstance(E.stockage(), E.store.StockageLocal):
            e["garmin_cle_locale"] = st.session_state.get("cle_saisie", "")
        E.sauver()
        E.aller("bienvenue", ob_etape=2)


def _importer(e, fichiers) -> int:
    man = e.setdefault("sorties_manuelles", [])
    ids = {m["id"] for m in man}
    n = 0
    for f in fichiers:
        try:
            s = importer(f.name, f.getvalue())
        except Exception:
            s = None
        if s and s["id"] not in ids:
            man.append(s)
            ids.add(s["id"])
            n += 1
    st.session_state.pop("donnees", None)
    E.invalider()
    return n


def _etape_import(e):
    titre("Je fouille<br>tes archives…", "", 40)
    if e.get("mode") == "demo":
        st.session_state.pop("donnees", None)
        E.donnees()
        E.aller("bienvenue", ob_etape=3)
    barre = st.progress(0.0, text=f"Connexion à {E.NOMS_MARQUES[E.marque()]}…")
    poids = {"Sorties": (0.0, 0.25), "VFC nocturne": (0.25, 0.4), "Sommeil": (0.4, 1.0)}

    def etape(nom, p):
        a, b = poids.get(nom, (0, 1))
        barre.progress(min(1.0, a + (b - a) * p), text=f"{nom}…")

    try:
        E.mettre_a_jour_garmin(etape)
    except Exception as err:
        st.error(f"Oups : {err}")
        if st.button("Revenir en arrière", key="retour1"):
            E.aller("bienvenue", ob_etape=1)
        return
    barre.progress(1.0, text="C'est fait !")
    E.aller("bienvenue", ob_etape=3)


def _etape_portrait(e):
    d = E.donnees()
    auj = E.aujourd_hui()
    titre("Voilà ce que j'ai<br>compris de toi", "", 34)
    port = coach.portrait(d, e.get("mois_exclus", []), auj)
    if port.nb_sorties == 0:
        html('<div class="f-bleu">Je n\'ai trouvé aucune sortie de course : pas grave, on partira en douceur '
             'et j\'apprendrai de tes premières séances.</div>')
    zone = f"{port.zone_vfc[0]:.0f}–{port.zone_vfc[1]:.0f} ms" if port.zone_vfc[0] else "en attente"
    tuiles([("Volume habituel", f"{port.volume_hebdo:.0f} km/sem", T.ENCRE),
            ("Plus longue sortie", f"{port.plus_longue:.0f} km", T.ENCRE)])
    tuiles([("Niveau estimé", f"VDOT {port.vdot:.0f}" if port.vdot else "–", T.ENCRE),
            ("Zone VFC", zone, T.BLEU)])
    if port.allures:
        a = port.allures
        html(f'<p class="f-sous" style="margin:0">Tes allures : footing {fmt_allure(a["E"][0])}–{fmt_allure(a["E"][1])}, '
             f'seuil {fmt_allure(sum(a["T"]) / 2)}, fractionné {fmt_allure(sum(a["I"]) / 2)} /km · '
             f'{port.nb_sorties} sorties, {port.nb_nuits_vfc} nuits de VFC.</p>')

    mois = _six_mois(auj)
    defaut = [lib for cle, lib in mois if cle in e.get("mois_exclus", [])]
    choix = st.pills("Un mois à ne pas compter ? (blessure, pause…)", [lib for _, lib in mois],
                     selection_mode="multi", default=defaut, key="pills_mois")
    nouveaux = sorted(cle for cle, lib in mois if lib in (choix or []))
    if nouveaux != sorted(e.get("mois_exclus", [])):
        e["mois_exclus"] = nouveaux
        E.sauver()
        st.rerun()
    if e.get("mois_exclus"):
        html(f'<p class="f-sous" style="margin:-4px 0 0">{len(e["mois_exclus"])} mois mis de côté : je recalcule sans.</p>')

    if st.button("C'est bien moi · mon objectif", key="accent_objectif"):
        E.aller("objectif", premiere_fois=True)


def _six_mois(auj: date):
    res = []
    a, m = auj.year, auj.month
    for _ in range(7):
        res.append((f"{a}-{m:02d}", MOIS[m - 1].rstrip(".").capitalize()))
        m -= 1
        if m == 0:
            a, m = a - 1, 12
    return list(reversed(res))
