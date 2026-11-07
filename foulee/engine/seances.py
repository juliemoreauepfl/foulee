"""Modèle de données des séances et petits utilitaires de format."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Optional

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_COURTS = ["L", "M", "M", "J", "V", "S", "D"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
              "septembre", "octobre", "novembre", "décembre"]
JOURS_ABR = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

# Types d'étape (repris pour l'export FIT)
ECHAUFFEMENT, EFFORT, RECUP, RETOUR, CONTINU = "echauffement", "effort", "recup", "retour", "continu"


@dataclass
class Etape:
    """Une étape de séance. Durée en secondes OU distance en mètres."""
    type: str
    duree_s: Optional[int] = None
    distance_m: Optional[int] = None
    allure_min: Optional[int] = None  # s/km, borne rapide
    allure_max: Optional[int] = None  # s/km, borne lente
    libelle: str = ""
    # Vélo : cible en % de FTP (0,65 = 65 %), watts si la FTP est connue, et repère cardio
    puissance_min: Optional[float] = None
    puissance_max: Optional[float] = None
    watts_min: Optional[int] = None
    watts_max: Optional[int] = None
    fc_min: Optional[int] = None
    fc_max: Optional[int] = None


@dataclass
class Bloc:
    etapes: list[Etape]
    repetitions: int = 1


@dataclass
class Seance:
    jour: date
    sport: str                # "course" | "renfo" | "velo" | "course_cible"
    genre: str                # footing, seuil, vma, cotes, specifique, long, course, renfo
    titre: str
    blocs: list[Bloc] = field(default_factory=list)
    km: float = 0.0
    minutes: int = 0
    note: str = ""
    allegee: bool = False     # modifiée par le coach
    origine: str = ""         # identifiant à la création du plan (pour les déplacements)
    reportee: bool = False    # replacée sur un autre jour après une annulation

    @property
    def ident(self) -> str:
        return f"{self.jour.isoformat()}-{self.genre}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["jour"] = self.jour.isoformat()
        return d


# ---------------------------------------------------------------- formats
def fmt_allure(s_km: Optional[float]) -> str:
    if not s_km:
        return "–"
    s = int(round(s_km))
    return f"{s // 60}:{s % 60:02d}"


def fmt_duree(sec: Optional[float], court: bool = False) -> str:
    if sec is None:
        return "–"
    sec = int(round(sec))
    h, reste = divmod(sec, 3600)
    m, s = divmod(reste, 60)
    if court:
        if h:
            return f"{h} h {m:02d}"
        return f"{m} min"
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fmt_km(km: float) -> str:
    return f"{km:.1f}".replace(".", ",") + " km"


def fmt_date(d: date, avec_jour: bool = True) -> str:
    txt = f"{d.day} {MOIS[d.month - 1]}"
    return f"{JOURS_ABR[d.weekday()]} {txt}" if avec_jour else txt


def parse_chrono(txt: str) -> Optional[int]:
    """'1:45:00', '45:30', '1h45' → secondes."""
    if not txt:
        return None
    t = txt.strip().lower().replace("h", ":").replace("min", "").replace("'", ":").replace(" ", "")
    if t.endswith(":"):
        t += "00"
    parts = [p for p in t.split(":") if p != ""]
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        # '1:45' ambigu : on considère h:mm si le premier nombre est petit (≤ 5)
        if nums[0] <= 5 and "h" in txt.lower():
            return nums[0] * 3600 + nums[1] * 60
        return nums[0] * 60 + nums[1]
    if len(nums) == 1:
        return nums[0] * 60
    return None


def resume_etapes(seance: Seance) -> list[tuple[str, str]]:
    """Lignes lisibles (libellé, allure) pour l'affichage."""
    lignes = []
    for bloc in seance.blocs:
        if bloc.repetitions > 1:
            effort = next((e for e in bloc.etapes if e.type == EFFORT), bloc.etapes[0])
            recup = next((e for e in bloc.etapes if e.type == RECUP), None)
            qte = _qte(effort)
            txt = f"{bloc.repetitions} × {qte}"
            if recup:
                txt += f", récup {_qte(recup)}"
            lignes.append((txt, _allure_txt(effort)))
        else:
            for e in bloc.etapes:
                nom = {ECHAUFFEMENT: "Échauffement", RETOUR: "Retour au calme", RECUP: e.libelle or "Récup",
                       CONTINU: e.libelle or "Footing", EFFORT: e.libelle or "Effort"}[e.type]
                lignes.append((f"{nom} · {_qte(e)}", _allure_txt(e)))
    return lignes


def _qte(e: Etape) -> str:
    if e.distance_m:
        return f"{e.distance_m / 1000:g} km".replace(".", ",") if e.distance_m >= 1000 else f"{e.distance_m} m"
    return fmt_duree(e.duree_s, court=True) if (e.duree_s or 0) >= 60 else f"{e.duree_s} s"


def _allure_txt(e: Etape) -> str:
    if e.puissance_min:
        if e.watts_min:
            txt = f"{e.watts_min}–{e.watts_max} W"
        else:
            txt = f"{round(e.puissance_min * 100)}–{round(e.puissance_max * 100)} % FTP"
        return txt + (f" · FC {e.fc_min}–{e.fc_max}" if e.fc_min else "")
    if e.allure_min and e.allure_max and abs(e.allure_max - e.allure_min) > 12:
        return f"{fmt_allure(e.allure_min)}–{fmt_allure(e.allure_max)} /km"
    if e.allure_min:
        return f"{fmt_allure((e.allure_min + (e.allure_max or e.allure_min)) / 2)} /km"
    return "au ressenti"
