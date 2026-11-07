"""État de session : stockage, données, navigation."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from .. import coach
from ..data import store
from ..data.donnees import Donnees, depuis_cache, donnees_demo, rafraichir
from ..data.garmin import ClientGarmin

RACINE = Path(__file__).resolve().parents[2]
PAGES_NAV = {"Aujourd'hui": "aujourdhui", "Semaine": "semaine", "Forme": "forme", "Objectif": "objectif"}


def secrets() -> dict:
    try:
        return {k: st.secrets[k] for k in st.secrets}
    except Exception:
        return {}


def aujourd_hui() -> date:
    fuseau = secrets().get("FUSEAU", "Europe/Paris")
    return datetime.now(ZoneInfo(fuseau)).date()


def stockage():
    if "stockage" not in st.session_state:
        st.session_state.stockage = store.ouvrir(secrets(), RACINE / "donnees")
    return st.session_state.stockage


def etat() -> dict:
    if "etat" not in st.session_state:
        try:
            e = stockage().lire("etat")
        except Exception as err:  # base injoignable : on ne perd rien, on prévient
            st.warning(f"Impossible de lire tes données sauvegardées ({err}). L'app tourne sans sauvegarde.")
            e = None
        base = coach.etat_initial()
        if e:
            base.update(e)
        st.session_state.etat = base
    return st.session_state.etat


def sauver():
    try:
        stockage().ecrire("etat", st.session_state.etat)
    except Exception as err:
        st.toast(f"Sauvegarde impossible : {err}")


def aller(page: str, **params):
    st.session_state.page = page
    for k, v in params.items():
        st.session_state[k] = v
    st.rerun()


def page_courante() -> str:
    if "page" not in st.session_state:
        st.session_state.page = "aujourdhui" if etat().get("onboarde") else "bienvenue"
    return st.session_state.page


def accent() -> str:
    return etat().get("accent", "#FF6B2C")


# ------------------------------------------------------------ Montre : Garmin ou Polar
NOMS_MARQUES = {"garmin": "Garmin", "polar": "Polar"}


def marque() -> str:
    return "polar" if etat().get("mode") == "polar" else "garmin"


def cle_garmin() -> str:
    return secrets().get("GARMIN_API_KEY") or st.session_state.get("cle_saisie") or etat().get("garmin_cle_locale", "")


def jeton_polar() -> dict:
    if "jeton_polar" not in st.session_state:
        try:
            st.session_state.jeton_polar = stockage().lire("polar_jeton", {}) or {}
        except Exception:
            st.session_state.jeton_polar = {}
    return st.session_state.jeton_polar


def connecte() -> bool:
    if etat().get("mode") in ("demo", "fichiers"):
        return False
    return bool(jeton_polar().get("access_token")) if marque() == "polar" else bool(cle_garmin())


def client():
    if marque() == "polar":
        from ..data.polar import ClientPolar
        return ClientPolar(jeton_polar())
    return ClientGarmin(cle_garmin())


def cle_cache() -> str:
    return f"cache_{marque()}"


def mettre_a_jour_garmin(etape=None) -> None:
    """Met à jour depuis la montre connectée (Garmin ou Polar)."""
    s = stockage()
    cache = s.lire(cle_cache(), {}) or {}
    nouveau = rafraichir(client(), cache, aujourd_hui(), etape)
    s.ecrire(cle_cache(), nouveau)
    st.session_state.pop("donnees", None)


def _ajouter_manuelles(d: Donnees) -> Donnees:
    man = etat().get("sorties_manuelles") or []
    if not man:
        return d
    df = pd.DataFrame(man)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    acts = pd.concat([d.activites, df], ignore_index=True) if not d.activites.empty else df
    return Donnees(acts.drop_duplicates("id", keep="last"), d.vfc, d.sommeil, d.source, d.maj, d.quotidien)


@st.cache_data(show_spinner=False)
def _demo(jour: date) -> Donnees:
    return donnees_demo(jour)


def donnees() -> Donnees:
    if "donnees" in st.session_state:
        return st.session_state.donnees
    e = etat()
    if e.get("mode") == "demo":
        d = _demo(aujourd_hui())
    else:
        cache = stockage().lire(cle_cache(), {}) or {}
        maj = cache.get("maj")
        vieux = not maj or datetime.fromisoformat(maj) < datetime.now() - timedelta(hours=1)
        nom = NOMS_MARQUES[marque()]
        if vieux and connecte():
            try:
                with st.spinner(f"Je récupère tes dernières données {nom}…"):
                    mettre_a_jour_garmin()
                cache = stockage().lire(cle_cache(), {}) or {}
            except Exception as err:
                st.warning(f"Mise à jour {nom} impossible pour l'instant : {err}")
        d = depuis_cache(cache)
        d.source = marque()
    d = _ajouter_manuelles(d)
    st.session_state.donnees = d
    return d


def contexte():
    ctx = st.session_state.get("contexte")
    if ctx is None or ctx.aujourd_hui != aujourd_hui():
        e = etat()
        avant = len(e.get("notes", []))
        st.session_state.contexte = coach.construire(e, donnees(), aujourd_hui())
        if len(e.get("notes", [])) != avant:
            sauver()
    return st.session_state.contexte


def invalider():
    """À appeler après une modification de l'état qui change le plan."""
    st.session_state.pop("contexte", None)
