"""Bibliothèque d'exercices de renforcement pour coureurs et composition des séances."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Iterable

RIEN, ELASTIQUE, KETTLEBELL = "rien", "elastique", "kettlebell"
NOMS_MATERIEL = {RIEN: "Sans matériel", ELASTIQUE: "Élastique", KETTLEBELL: "Kettlebell"}
CHOIX_MATERIEL = {RIEN: "Rien", ELASTIQUE: "Élastiques", KETTLEBELL: "Kettlebell"}

# Rôles dans une séance : un exercice par rôle
FESSIERS, CUISSES, MOLLETS, GAINAGE, EQUILIBRE = "fessiers", "cuisses", "mollets", "gainage", "equilibre"
ORDRE_ROLES = [FESSIERS, CUISSES, MOLLETS, GAINAGE, EQUILIBRE]


@dataclass(frozen=True)
class Exo:
    id: str
    nom: str
    materiel: str
    role: str
    zone: str                 # étiquette affichée
    phrase: str               # la phrase ludique
    etapes: tuple[str, str, str]
    pourquoi: str
    oups: str
    plus_dur: str
    reps: str
    soulage: tuple[str, ...] = ()   # zones de douleur que l'exercice aide à protéger

    @property
    def image(self) -> str:
        return f"{self.id}.svg"


BIBLIOTHEQUE: list[Exo] = [
    Exo("pont-levis", "Le pont-levis", RIEN, FESSIERS, "Fessiers",
        "Les hanches montent, les chevaliers passent.",
        ("Sur le dos, genoux pliés, pieds à plat.", "Pousse dans les talons, hanches au ciel.", "Tiens 2 s, redescends en 3 s."),
        "Des fessiers réveillés = une poussée plus puissante et des genoux protégés.",
        "Ne cambre pas le bas du dos : c'est le bassin qui monte.",
        "Une jambe tendue en l'air.", "3 × 12", ("genou", "hanche", "dos")),
    Exo("fente-mousquetaire", "La fente du mousquetaire", RIEN, CUISSES, "Cuisses",
        "En garde ! Genou arrière qui frôle le sol.",
        ("Debout, un grand pas en avant.", "Descends : genou arrière à un doigt du sol.", "Pousse sur le talon avant pour remonter."),
        "Chaque foulée est une petite fente : on muscle exactement le geste.",
        "Le genou avant ne part pas vers l'intérieur.",
        "Fente arrière sautée, en douceur.", "3 × 10 par jambe", ("genou",)),
    Exo("girafe", "La girafe", RIEN, MOLLETS, "Mollets",
        "Sur la pointe des pieds, attrape le haut de l'arbre.",
        ("Debout, au bord d'une marche.", "Monte sur la pointe des pieds.", "Redescends lentement, talons sous la marche."),
        "Mollets et tendons d'Achille encaissent 2 à 3 fois ton poids à chaque appui.",
        "Pas de rebond : la descente est lente.",
        "Sur une seule jambe.", "3 × 15", ("achille", "mollet", "pied")),
    Exo("planche", "La planche à repasser", RIEN, GAINAGE, "Gainage",
        "Toute droite, pas un pli. On respire.",
        ("Appui sur les avant-bras et les pointes de pieds.", "Corps aligné de la tête aux talons.", "Respire calmement, nombril rentré."),
        "Un tronc solide = moins d'énergie perdue en fin de course.",
        "Les fesses ne pointent pas vers le ciel.",
        "Lève un pied, puis l'autre.", "3 × 30 s", ("dos",)),
    Exo("flamant-rose", "Le flamant rose", RIEN, EQUILIBRE, "Équilibre",
        "Une jambe, un buste qui bascule, zéro chute.",
        ("Debout sur une jambe, genou souple.", "Bascule le buste, l'autre jambe part en arrière.", "Remonte en serrant la fesse d'appui."),
        "Chevilles et hanches stables = moins d'entorses sur les chemins.",
        "Le dos reste plat, comme une table.",
        "Les yeux fermés (près d'un mur !).", "3 × 8 par jambe", ("cheville", "pied", "hanche")),
    Exo("chaise-invisible", "La chaise invisible", RIEN, CUISSES, "Cuisses",
        "Assise contre le mur… sans chaise.",
        ("Dos collé au mur.", "Glisse jusqu'à genoux à 90°.", "Tiens, en respirant."),
        "Des quadriceps endurants pour les descentes et la fin de course.",
        "Genoux au-dessus des chevilles, pas plus loin.",
        "Sur une jambe, quelques secondes.", "3 × 40 s", ("genou",)),
    Exo("requin", "Le requin", RIEN, GAINAGE, "Gainage latéral",
        "Sur le côté, la hanche fait l'aileron.",
        ("Sur le côté, appui sur l'avant-bras.", "Lève les hanches : corps bien droit.", "Tiens, puis change de côté."),
        "Le gainage latéral empêche le bassin de s'affaisser à chaque appui.",
        "Les hanches ne retombent pas.",
        "Lève la jambe du dessus.", "3 × 25 s par côté", ("hanche", "dos")),
    Exo("alpiniste", "L'alpiniste", RIEN, GAINAGE, "Gainage + cardio",
        "Les genoux grimpent, le dos reste plat.",
        ("Position de pompe, bras tendus.", "Ramène un genou vers la poitrine.", "Alterne vite, sans lever les fesses."),
        "Gainage dynamique : le tronc tient pendant que les jambes bougent, comme en course.",
        "Les épaules restent au-dessus des mains.",
        "Plus vite, 40 s.", "3 × 30 s", ()),
    Exo("tabouret-fantome", "Le tabouret fantôme", RIEN, CUISSES, "Cuisses",
        "Assieds-toi sur un tabouret qui n'existe pas.",
        ("Pieds largeur de hanches.", "Fesses en arrière, descends comme pour t'asseoir.", "Remonte en poussant le sol."),
        "Le squat, c'est la base : cuisses, fessiers et genoux plus costauds.",
        "Les talons restent collés au sol.",
        "Descente en 4 secondes.", "3 × 15", ("genou",)),
    Exo("crabe", "Le crabe", ELASTIQUE, EQUILIBRE, "Hanches",
        "Pas chassés, élastique tendu, pince pince.",
        ("Élastique au-dessus des genoux ou aux chevilles.", "Demi-flexion, dos droit.", "Petits pas de côté, élastique toujours tendu."),
        "Le moyen fessier tient ton bassin droit : meilleur ami des genoux.",
        "Les pieds ne se touchent jamais.",
        "Élastique aux chevilles.", "3 × 12 pas par côté", ("genou", "hanche")),
    Exo("huitre", "L'huître", ELASTIQUE, EQUILIBRE, "Hanches",
        "Sur le côté, le genou s'ouvre comme une huître.",
        ("Sur le côté, genoux pliés, élastique aux genoux.", "Pieds collés, ouvre le genou du dessus.", "Referme lentement."),
        "Cible les petits muscles de hanche souvent endormis chez les coureurs.",
        "Le bassin ne roule pas en arrière.",
        "Hanches décollées en appui sur l'avant-bras.", "3 × 15 par côté", ("genou", "hanche")),
    Exo("ruade-poney", "La ruade du poney", ELASTIQUE, FESSIERS, "Fessiers",
        "À quatre pattes, le talon pousse vers le ciel.",
        ("À quatre pattes, élastique sous la main et autour du pied.", "Pousse le talon vers l'arrière et le haut.", "Reviens sans toucher le sol."),
        "Le grand fessier propulse : c'est ton moteur de foulée.",
        "Le dos ne se creuse pas.",
        "Élastique plus dur.", "3 × 12 par jambe", ("hanche", "dos")),
    Exo("pont-elastique", "Le pont-levis blindé", ELASTIQUE, FESSIERS, "Fessiers",
        "Le pont-levis, avec élastique aux genoux.",
        ("Sur le dos, élastique au-dessus des genoux.", "Écarte un peu les genoux et monte les hanches.", "Tiens 2 s en haut, redescends lentement."),
        "Fessiers + hanches en même temps : genoux bien alignés en course.",
        "Les genoux ne se rapprochent pas.",
        "Sur une jambe.", "3 × 12", ("genou", "hanche")),
    Exo("ressort", "Le ressort", ELASTIQUE, CUISSES, "Cuisses",
        "Un squat avec un ressort aux genoux.",
        ("Élastique juste au-dessus des genoux.", "Fesses en arrière, descends en poussant les genoux vers l'extérieur.", "Remonte d'un coup, comme un ressort."),
        "Cuisses et fessiers ensemble, genoux bien alignés : le combo anti-bobos.",
        "Les genoux ne rentrent pas vers l'intérieur.",
        "Petit saut en haut.", "3 × 12", ("genou", "hanche")),
    Exo("coffre-fort", "Le coffre-fort", ELASTIQUE, GAINAGE, "Gainage",
        "L'élastique tire, tu ne bouges pas d'un millimètre.",
        ("Élastique accroché sur le côté (poignée de porte, poteau).", "Mains contre la poitrine, tends les bras devant toi.", "Tiens 2 s sans tourner, reviens."),
        "Un tronc qui résiste à la rotation : moins de balancier, plus d'efficacité.",
        "Le buste ne pivote pas vers l'élastique.",
        "Fais un pas de plus loin du point d'accroche.", "3 × 10 par côté", ("dos",)),
    Exo("balancier", "Le balancier", KETTLEBELL, FESSIERS, "Chaîne arrière",
        "Les hanches propulsent, les bras suivent.",
        ("Pieds écartés, kettlebell entre les jambes.", "Hanches en arrière, puis claque-les vers l'avant.", "La cloche monte à hauteur d'épaules, sans tirer des bras."),
        "Puissance des hanches = foulée qui rebondit et montées plus faciles.",
        "Ce n'est pas un squat : on plie les hanches, pas les genoux.",
        "Kettlebell plus lourde.", "3 × 15", ("dos",)),
    Exo("gobelet", "Le squat gobelet", KETTLEBELL, CUISSES, "Cuisses",
        "La kettlebell contre toi, comme un gros chocolat chaud.",
        ("Kettlebell tenue contre la poitrine.", "Descends, coudes entre les genoux.", "Remonte en poussant le sol."),
        "Cuisses et fessiers plus forts, posture droite garantie.",
        "Le buste reste fier, la tasse ne se renverse pas.",
        "Pause de 2 s en bas.", "3 × 10", ("genou",)),
    Exo("flamant-charge", "Le flamant fait ses courses", KETTLEBELL, EQUILIBRE, "Équilibre",
        "Le flamant rose, kettlebell en main.",
        ("Sur une jambe, kettlebell dans la main opposée.", "Bascule le buste, la cloche descend vers le pied.", "Remonte en serrant la fesse d'appui."),
        "Ischios et fessiers d'une jambe à la fois : comme en course.",
        "Le dos reste plat.",
        "Plus lourd, ou pause en bas.", "3 × 8 par jambe", ("cheville", "hanche")),
    Exo("porteur-valise", "Le porteur de valise", KETTLEBELL, GAINAGE, "Gainage",
        "Marche fière, une valise d'un côté, buste droit.",
        ("Kettlebell dans une main, bras le long du corps.", "Marche lentement, épaules à l'horizontale.", "Change de main au retour."),
        "Gainage latéral en mouvement : ton bassin reste stable en courant.",
        "Pas de penché vers la valise.",
        "Kettlebell plus lourde.", "3 × 30 m par côté", ("dos", "hanche")),
    Exo("escalier-chateau", "L'escalier du donjon", KETTLEBELL, MOLLETS, "Cuisses + mollets",
        "Monte au donjon, une marche à la fois.",
        ("Un pied sur une marche ou un banc solide.", "Pousse sur ce pied pour monter, sans t'aider de l'autre.", "Redescends doucement."),
        "Le geste de la côte : force d'une jambe et poussée des mollets.",
        "Le genou suit l'axe du pied.",
        "Monte sur la pointe du pied en haut.", "3 × 8 par jambe", ("genou", "mollet")),
]

PAR_ID = {e.id: e for e in BIBLIOTHEQUE}

NOMS_SEANCES = {
    RIEN: ("Jambes de feu", "Zéro matériel, zéro excuse. Fessiers et mollets solides = foulée qui rebondit."),
    ELASTIQUE: ("Élastique fantastique", "L'élastique réveille les petits muscles des hanches qui protègent tes genoux."),
    KETTLEBELL: ("Boulet de canon", "Un peu de poids pour une chaîne arrière en béton armé."),
}


def materiel_autorise(choix: str) -> set[str]:
    return {RIEN, choix}


def composer_seance(choix: str, jour: date, favoris: Iterable[str] = (), bannis: Iterable[str] = (),
                    douleurs: Iterable[str] = (), nb: int = 5) -> list[Exo]:
    """Choisit nb exercices, un par rôle, en respectant le matériel, les favoris,
    les exercices bannis et les zones douloureuses récentes. Le tirage est stable
    pour un même jour (la séance ne change pas à chaque ouverture)."""
    favoris, bannis, douleurs = set(favoris), set(bannis), set(douleurs)
    autorise = materiel_autorise(choix)
    pool = [e for e in BIBLIOTHEQUE if e.materiel in autorise and e.id not in bannis]
    rng = random.Random(f"{jour.isoformat()}-{choix}")

    def poids(e: Exo) -> float:
        w = 1.0
        if e.id in favoris:
            w *= 3
        if choix != RIEN and e.materiel == choix:
            w *= 6
        if douleurs & set(e.soulage):
            w *= 3
        return w

    choisis: list[Exo] = []
    for role in ORDRE_ROLES[:nb]:
        candidats = [e for e in pool if e.role == role and e not in choisis]
        if not candidats:
            continue
        choisis.append(rng.choices(candidats, weights=[poids(e) for e in candidats])[0])
    restants = [e for e in pool if e not in choisis]
    while len(choisis) < nb and restants:
        e = rng.choices(restants, weights=[poids(x) for x in restants])[0]
        choisis.append(e)
        restants.remove(e)
    return choisis


def duree_estimee(exos: list[Exo]) -> int:
    return max(10, round(len(exos) * 4.2))
