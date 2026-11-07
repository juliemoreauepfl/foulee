"""Lecture et écriture minimales du format FIT de Garmin.

- `ecrire_seance` produit un fichier de séance structurée (workout) à copier
  dans le dossier GARMIN/NewFiles de la montre.
- `lire_tours` extrait les tours (laps) d'un fichier d'activité, pour comparer
  chaque bloc aux allures prévues.

Implémentation autonome d'après le FIT SDK publié par Garmin : pas de
dépendance externe."""
from __future__ import annotations

import io
import struct
import zipfile
from datetime import datetime, timezone
from typing import Optional

from ..engine.seances import CONTINU, ECHAUFFEMENT, EFFORT, RECUP, RETOUR, Seance

EPOQUE_FIT = datetime(1989, 12, 31, tzinfo=timezone.utc)

_CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def crc16(data: bytes, crc: int = 0) -> int:
    for b in data:
        t = _CRC[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ t ^ _CRC[b & 0xF]
        t = _CRC[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ t ^ _CRC[(b >> 4) & 0xF]
    return crc


# Types de base FIT : code → (taille, format struct, valeur invalide)
BASE = {
    0x00: (1, "B", 0xFF),        # enum
    0x01: (1, "b", 0x7F),        # sint8
    0x02: (1, "B", 0xFF),        # uint8
    0x83: (2, "h", 0x7FFF),      # sint16
    0x84: (2, "H", 0xFFFF),      # uint16
    0x85: (4, "i", 0x7FFFFFFF),  # sint32
    0x86: (4, "I", 0xFFFFFFFF),  # uint32
    0x07: (1, "s", None),        # string
    0x88: (4, "f", None),        # float32
    0x89: (8, "d", None),        # float64
    0x0A: (1, "B", 0x00),        # uint8z
    0x8B: (2, "H", 0x0000),      # uint16z
    0x8C: (4, "I", 0x00000000),  # uint32z
    0x0D: (1, "B", None),        # byte
    0x8E: (8, "q", 0x7FFFFFFFFFFFFFFF),  # sint64
    0x8F: (8, "Q", 0xFFFFFFFFFFFFFFFF),  # uint64
    0x90: (8, "Q", 0x0000000000000000),  # uint64z
}
ENUM, UINT8, UINT16, UINT32, STRING, UINT32Z = 0x00, 0x02, 0x84, 0x86, 0x07, 0x8C

# Messages globaux utilisés
FILE_ID, WORKOUT, WORKOUT_STEP, LAP, SESSION = 0, 26, 27, 19, 18

# workout_step : énumérations du profil FIT
DUREE_TEMPS, DUREE_DISTANCE, DUREE_OUVERTE, DUREE_REPETER = 0, 1, 5, 6
CIBLE_VITESSE, CIBLE_FC, CIBLE_OUVERTE, CIBLE_PUISSANCE = 0, 1, 2, 4
INTENSITE = {EFFORT: 0, CONTINU: 0, RECUP: 4, ECHAUFFEMENT: 2, RETOUR: 3}


class _Ecrivain:
    def __init__(self):
        self.buf = bytearray()
        self.definis: dict[int, tuple] = {}

    def message(self, local: int, global_num: int, champs: list[tuple[int, int, int, object]]):
        """champs : (numéro, type de base, taille, valeur)."""
        signature = tuple((n, t, s) for n, t, s, _ in champs)
        if self.definis.get(local) != (global_num, signature):
            self.buf += bytes([0x40 | local, 0, 0]) + struct.pack("<HB", global_num, len(champs))
            for n, t, s, _ in champs:
                self.buf += bytes([n, s, t])
            self.definis[local] = (global_num, signature)
        self.buf += bytes([local])
        for n, t, s, v in champs:
            if t == STRING:
                b = (v or "").encode("utf-8")[: s - 1]
                self.buf += b + b"\x00" * (s - len(b))
            else:
                taille, fmt, invalide = BASE[t]
                self.buf += struct.pack("<" + fmt, invalide if v is None else int(v))

    def fichier(self) -> bytes:
        entete = struct.pack("<BBHI4s", 14, 0x10, 2132, len(self.buf), b".FIT")
        entete += struct.pack("<H", crc16(entete))
        corps = entete + bytes(self.buf)
        return corps + struct.pack("<H", crc16(corps))


def _vitesse_mm_s(allure_s_km: Optional[float]) -> Optional[int]:
    if not allure_s_km:
        return None
    return int(round(1_000_000 / allure_s_km))  # (1000 m / allure s) × 1000


def ecrire_seance(seance: Seance, nom: Optional[str] = None, maintenant: Optional[datetime] = None) -> bytes:
    """Fichier FIT « workout » de course à pied, avec répétitions et cibles d'allure."""
    w = _Ecrivain()
    t = int(((maintenant or datetime.now(timezone.utc)) - EPOQUE_FIT).total_seconds())
    w.message(0, FILE_ID, [(0, ENUM, 1, 5), (1, UINT16, 2, 255), (2, UINT16, 2, 0),
                           (3, UINT32Z, 4, 12345), (4, UINT32, 4, t)])

    etapes = []  # (etape ou None si répétition, info répétition)
    for bloc in seance.blocs:
        debut = len(etapes)
        for e in bloc.etapes:
            etapes.append(("etape", e))
        if bloc.repetitions > 1:
            etapes.append(("repeter", (debut, bloc.repetitions)))

    titre = (nom or seance.titre).replace("·", "-")
    sport = 2 if seance.sport == "velo" else 1   # 2 = vélo, 1 = course
    w.message(1, WORKOUT, [(4, ENUM, 1, sport), (6, UINT16, 2, len(etapes)), (8, STRING, 32, titre)])

    for i, (genre, val) in enumerate(etapes):
        if genre == "repeter":
            debut, n = val
            champs = [(254, UINT16, 2, i), (0, STRING, 16, f"Repeter x{n}"),
                      (1, ENUM, 1, DUREE_REPETER), (2, UINT32, 4, debut), (3, ENUM, 1, CIBLE_OUVERTE),
                      (4, UINT32, 4, n), (5, UINT32, 4, None), (6, UINT32, 4, None), (7, ENUM, 1, 0)]
        else:
            e = val
            if e.distance_m:
                d_type, d_val = DUREE_DISTANCE, int(e.distance_m * 100)
            elif e.duree_s:
                d_type, d_val = DUREE_TEMPS, int(e.duree_s * 1000)
            else:
                d_type, d_val = DUREE_OUVERTE, None
            if e.puissance_min and e.puissance_max:
                # Valeurs de 0 à 1000 = % de FTP : la montre/le compteur utilise ta FTP enregistrée
                c_type = CIBLE_PUISSANCE
                bas, haut = round(e.puissance_min * 100), round(e.puissance_max * 100)
            elif e.allure_min and e.allure_max:
                c_type = CIBLE_VITESSE
                bas, haut = _vitesse_mm_s(e.allure_max), _vitesse_mm_s(e.allure_min)
            else:
                c_type, bas, haut = CIBLE_OUVERTE, None, None
            nom_etape = {ECHAUFFEMENT: "Echauffement", RETOUR: "Retour calme", RECUP: "Recup",
                         EFFORT: "Effort", CONTINU: "Footing"}[e.type]
            champs = [(254, UINT16, 2, i), (0, STRING, 16, nom_etape), (1, ENUM, 1, d_type),
                      (2, UINT32, 4, d_val), (3, ENUM, 1, c_type), (4, UINT32, 4, 0 if c_type in (CIBLE_VITESSE, CIBLE_PUISSANCE) else None),
                      (5, UINT32, 4, bas), (6, UINT32, 4, haut), (7, ENUM, 1, INTENSITE[e.type])]
        w.message(2, WORKOUT_STEP, champs)
    return w.fichier()


# ------------------------------------------------------------------ lecture
class FitErreur(Exception):
    pass


def lire_messages(data: bytes) -> list[tuple[int, dict]]:
    """Décode un fichier FIT en liste (numéro global, {champ: valeur brute})."""
    if len(data) < 12:
        raise FitErreur("fichier trop court")
    taille_entete = data[0]
    if data[8:12] != b".FIT":
        raise FitErreur("ce n'est pas un fichier FIT")
    taille_donnees = struct.unpack_from("<I", data, 4)[0]
    pos, fin = taille_entete, min(taille_entete + taille_donnees, len(data))
    defs: dict[int, dict] = {}
    sortie = []
    while pos < fin:
        h = data[pos]
        pos += 1
        if h & 0x80:  # en-tête compressé (horodatage)
            local = (h >> 5) & 0x03
            d = defs.get(local)
            if d is None:
                raise FitErreur("définition manquante")
            pos = _lire_donnees(data, pos, d, sortie)
        elif h & 0x40:  # définition
            local = h & 0x0F
            archi = data[pos + 1]
            endian = ">" if archi == 1 else "<"
            glob = struct.unpack_from(endian + "H", data, pos + 2)[0]
            nb = data[pos + 4]
            pos += 5
            champs = []
            for _ in range(nb):
                champs.append((data[pos], data[pos + 1], data[pos + 2]))
                pos += 3
            dev = 0
            if h & 0x20:
                nbd = data[pos]
                pos += 1
                for _ in range(nbd):
                    dev += data[pos + 1]
                    pos += 3
            defs[local] = {"global": glob, "endian": endian, "champs": champs, "dev": dev}
        else:
            d = defs.get(h & 0x0F)
            if d is None:
                raise FitErreur("définition manquante")
            pos = _lire_donnees(data, pos, d, sortie)
    return sortie


def _lire_donnees(data, pos, d, sortie):
    valeurs = {}
    for num, taille, base in d["champs"]:
        brut = data[pos:pos + taille]
        pos += taille
        info = BASE.get(base & 0x9F) or BASE.get(base)
        if info is None:
            continue
        t, fmt, invalide = info
        if fmt == "s":
            valeurs[num] = brut.split(b"\x00")[0].decode("utf-8", "replace")
            continue
        if taille != t:
            if taille % t == 0 and taille > t:  # tableau : on garde le premier élément
                brut = brut[:t]
            else:
                continue
        v = struct.unpack(d["endian"] + fmt, brut)[0]
        valeurs[num] = None if (invalide is not None and v == invalide) else v
    pos += d["dev"]
    sortie.append((d["global"], valeurs))
    return pos


def verifier_crc(data: bytes) -> bool:
    taille_entete = data[0]
    taille_donnees = struct.unpack_from("<I", data, 4)[0]
    total = taille_entete + taille_donnees
    return crc16(data[:total]) == struct.unpack_from("<H", data, total)[0]


def extraire_fit(contenu: bytes) -> bytes:
    """Garmin renvoie souvent un ZIP contenant le .fit."""
    if contenu[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(contenu)) as z:
            noms = [n for n in z.namelist() if n.lower().endswith(".fit")] or z.namelist()
            return z.read(noms[0])
    return contenu


def lire_tours(contenu: bytes) -> list[dict]:
    """Tours (laps) : durée, distance, FC moyenne, allure (s/km)."""
    msgs = lire_messages(extraire_fit(contenu))
    tours = []
    for glob, v in msgs:
        if glob != LAP:
            continue
        duree = (v.get(8) or v.get(7) or 0) / 1000   # total_timer_time, sinon total_elapsed_time
        dist = (v.get(9) or 0) / 100                 # total_distance
        vit = v.get(110) or v.get(13)                # enhanced_avg_speed, avg_speed (mm/s)
        allure = 1_000_000 / vit if vit else (duree / (dist / 1000) if dist else None)
        tours.append({"duree_s": duree, "distance_m": dist, "fc_moy": v.get(15), "allure": allure})
    return tours
