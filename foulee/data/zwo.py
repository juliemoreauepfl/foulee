"""Export d'une séance de vélo au format .zwo (Zwift et d'autres apps de home trainer)."""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..engine.seances import CONTINU, ECHAUFFEMENT, EFFORT, RECUP, RETOUR, Seance


def _p(x: float) -> str:
    return f"{x:.2f}"


def ecrire_zwo(seance: Seance) -> bytes:
    lignes = []
    for b in seance.blocs:
        eff = next((e for e in b.etapes if e.type == EFFORT), None)
        rec = next((e for e in b.etapes if e.type == RECUP), None)
        if b.repetitions > 1 and eff and rec:
            lignes.append(f'<IntervalsT Repeat="{b.repetitions}" OnDuration="{eff.duree_s}" OffDuration="{rec.duree_s}" '
                          f'OnPower="{_p((eff.puissance_min + eff.puissance_max) / 2)}" '
                          f'OffPower="{_p((rec.puissance_min + rec.puissance_max) / 2)}"/>')
            continue
        for e in b.etapes:
            lo, hi = e.puissance_min or 0.5, e.puissance_max or 0.6
            if e.type == ECHAUFFEMENT:
                lignes.append(f'<Warmup Duration="{e.duree_s}" PowerLow="{_p(lo)}" PowerHigh="{_p(hi)}"/>')
            elif e.type == RETOUR:
                lignes.append(f'<Cooldown Duration="{e.duree_s}" PowerLow="{_p(hi)}" PowerHigh="{_p(lo)}"/>')
            else:
                lignes.append(f'<SteadyState Duration="{e.duree_s}" Power="{_p((lo + hi) / 2)}"/>')
    xml = ("<workout_file><author>Foulée</author>"
           f"<name>{escape(seance.titre)}</name>"
           f"<description>{escape(seance.note)}</description>"
           "<sportType>bike</sportType><tags/><workout>" + "".join(lignes) + "</workout></workout_file>")
    return xml.encode("utf-8")
