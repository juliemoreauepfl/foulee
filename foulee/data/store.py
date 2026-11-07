"""Stockage de l'état de l'app (profil, bilans, favoris…) et du cache des données.

- En ligne : une table Supabase (gratuite) si SUPABASE_URL et SUPABASE_KEY sont
  dans les secrets Streamlit.
- Sinon : un fichier JSON local (dossier `donnees/`), parfait sur ton ordi.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

import requests

TABLE = "foulee"


def _json_defaut(o):
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(f"Non sérialisable : {type(o)}")


class StockageLocal:
    nom = "fichier local"

    def __init__(self, dossier: Path):
        self.dossier = Path(dossier)
        self.dossier.mkdir(parents=True, exist_ok=True)

    def _chemin(self, cle: str) -> Path:
        return self.dossier / f"{cle}.json"

    def lire(self, cle: str, defaut: Any = None) -> Any:
        p = self._chemin(cle)
        if not p.exists():
            return defaut
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return defaut

    def ecrire(self, cle: str, valeur: Any) -> None:
        tmp = self._chemin(cle).with_suffix(".tmp")
        tmp.write_text(json.dumps(valeur, default=_json_defaut, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._chemin(cle))

    def effacer(self, cle: str) -> None:
        self._chemin(cle).unlink(missing_ok=True)


class StockageSupabase:
    nom = "Supabase"

    def __init__(self, url: str, cle: str, prefixe: str = ""):
        self.url = url.rstrip("/") + f"/rest/v1/{TABLE}"
        self.prefixe = prefixe
        self.h = {"apikey": cle, "Content-Type": "application/json"}
        if cle.startswith("eyJ"):  # ancienne clé service_role (JWT) : acceptée aussi en Bearer
            self.h["Authorization"] = f"Bearer {cle}"
        # Les nouvelles clés sb_secret_… ne sont pas des JWT : uniquement dans l'en-tête apikey

    def lire(self, cle: str, defaut: Any = None) -> Any:
        r = requests.get(self.url, headers=self.h, timeout=20,
                         params={"cle": f"eq.{self.prefixe}{cle}", "select": "valeur"})
        r.raise_for_status()
        rows = r.json()
        return rows[0]["valeur"] if rows else defaut

    def ecrire(self, cle: str, valeur: Any) -> None:
        corps = json.dumps([{"cle": f"{self.prefixe}{cle}", "valeur": valeur}], default=_json_defaut, ensure_ascii=False)
        r = requests.post(self.url, headers={**self.h, "Prefer": "resolution=merge-duplicates"},
                          params={"on_conflict": "cle"}, data=corps.encode("utf-8"), timeout=30)
        r.raise_for_status()

    def effacer(self, cle: str) -> None:
        requests.delete(self.url, headers=self.h, params={"cle": f"eq.{self.prefixe}{cle}"}, timeout=20)


def ouvrir(secrets: Optional[dict], dossier_local: Path, prefixe: str = ""):
    secrets = secrets or {}
    url, cle = secrets.get("SUPABASE_URL"), secrets.get("SUPABASE_KEY")
    if url and cle:
        return StockageSupabase(url, cle, prefixe)
    return StockageLocal(dossier_local / (prefixe.rstrip("-") or "perso"))
