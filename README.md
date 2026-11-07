# Foulée 🧡 ton coach de course à pied de poche

Plan d'entraînement course à pied (+ vélo / home trainer en complément) qui part de **ton** historique Garmin ou Polar, s'ajuste à ta VFC, à tes bilans
et à tes douleurs, avec des séances de renfo ludiques selon le matériel du jour.

---

## 1. L'essayer sur ton ordi (5 minutes, mode démo)

Dans VS Code : **Fichier › Ouvrir le dossier…** › choisis le dossier `foulee`, puis
**Terminal › Nouveau terminal** et tape, ligne par ligne :

```bash
python -m venv .venv
.venv\Scripts\activate          # sur Mac/Linux : source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Ton navigateur s'ouvre sur l'app. Clique **« Essayer avec des données de démo »**.
Pour arrêter : `Ctrl + C` dans le terminal.

**Avec tes vraies données :** dans l'écran d'accueil, colle ta clé Garmin Personal
(Garmin Connect sur le web › Paramètres › *Personal API Token* › *Créer une clé*, durée : 1 an).

---

## 2. La mettre sur ton iPhone (gratuit)

Trois comptes gratuits : **GitHub** (le code), **Supabase** (la sauvegarde), **Streamlit
Community Cloud** (l'app en ligne).

### a. Le code sur GitHub
1. Crée un compte sur [github.com](https://github.com).
2. Dans VS Code : icône **Contrôle de code source** (à gauche) › **Publier sur GitHub** ›
   *Dépôt public*. Le code ne contient aucune donnée perso : tes secrets restent ailleurs
   (le fichier `.gitignore` y veille).

### b. La sauvegarde sur Supabase
1. Crée un compte sur [supabase.com](https://supabase.com) › **New project** (région : Europe).
2. **SQL Editor › New query** › colle le contenu de `supabase.sql` › **Run**.
3. **Project Settings › API Keys** : note l'**URL du projet** et une **clé secrète** (`sb_secret_…`).

> Un projet gratuit se met en pause après 7 jours sans aucune visite. Si ça arrive,
> un clic sur « Restore » dans Supabase le réveille, rien n'est perdu.

### c. L'app sur Streamlit Cloud
1. Va sur [share.streamlit.io](https://share.streamlit.io) › connecte-toi avec GitHub.
2. **Create app** › ton dépôt `foulee` › fichier principal : `app.py`.
3. **Advanced settings › Secrets** › colle ceci en remplaçant les valeurs :
   ```toml
   GARMIN_API_KEY = "ta-cle-garmin"
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "sb_secret_xxxx"
   APP_PASSWORD = "un-mot-de-passe-a-toi"
   ```
4. **Deploy**. Dans les réglages de partage de l'app, choisis qu'elle ne soit visible que
   par toi si l'option est proposée. Le mot de passe protège de toute façon l'entrée.

### d. L'icône sur l'iPhone
Ouvre le lien de ton app dans **Safari** › bouton **Partager** › **Sur l'écran d'accueil**.

Quand tu modifies le code et le republies sur GitHub, l'app se met à jour toute seule.

---

## 2 bis. Avec une montre Polar

Polar a aussi une API gratuite (AccessLink), avec deux différences :
- **Elle ne garde que les 30 derniers jours.** Au début, le plan part donc de ton dernier mois.
  Ensuite, l'app accumule ton historique dans sa sauvegarde : ouvre-la au moins une fois par mois.
  Pour tes anciennes sorties, tu peux les importer en fichiers .FIT/.GPX exportés depuis Polar Flow.
- **Pas d'envoi de séance vers la montre** (comme Garmin) : tu recrées la séance dans Polar Flow
  (objectif d'entraînement par phases).

Mise en place (5 min) :
1. Sur [admin.polaraccesslink.com](https://admin.polaraccesslink.com), connecte-toi avec ton compte
   Polar Flow et crée un client.
2. Lien de retour (*Authorization callback / redirect URL*) : l'adresse de ton app **suivie d'un /**,
   par exemple `https://ton-app.streamlit.app/` (en local : `http://localhost:8501/`).
3. Dans les secrets, à la place de `GARMIN_API_KEY` :
   ```toml
   POLAR_CLIENT_ID = "ton-client-id"
   POLAR_CLIENT_SECRET = "ton-client-secret"
   APP_URL = "https://ton-app.streamlit.app"
   ```
4. Dans l'app : « Ta montre : Polar » › **Connecter mon compte Polar** › accepte › tu reviens dans l'app.

---

## 3. Partager avec des amis

Chacun a **sa propre copie** (son code, sa clé, ses données) : voir [GUIDE_AMIS.md](GUIDE_AMIS.md).
La clé Garmin Personal est réservée à un usage personnel, avec ses propres données :
c'est pour ça qu'on ne mélange jamais les données de plusieurs personnes.

---

## Comment pense le coach

| Brique | Méthode publique utilisée |
|---|---|
| Niveau et allures | Équations de Daniels & Gilbert (VDOT), + estimation par la fréquence cardiaque (%FC de réserve ≈ %VO2 de réserve) |
| Charge | TRIMP de Banister, modèle forme (42 j) / fatigue (7 j) |
| Plan | Base → développement → spécifique → affûtage ; +8 %/semaine max, semaine allégée toutes les 4 ; ~80 % en facile |
| VFC | Moyenne 7 nuits vs zone habituelle (zone Garmin si dispo, sinon 60 nuits ± 1 écart-type) |
| Ajustements | Règles simples, toujours expliquées par une note du coach |

Règles d'ajustement :
- VFC sous ta zone le jour d'une séance dure → footing tranquille ; « orage » → balade de 25 min.
- 2 séances bien plus dures que prévu en 10 jours → −8 % de volume et allures un peu plus lentes.
- 2 séances de qualité très faciles → allures ~1,5 % plus rapides.
- Douleur signalée → sortie longue suivante raccourcie et renfo ciblé ; même zone 2 fois en 14 jours → semaine à −30 % sans intensité.
- 3 séances sautées sur 14 jours → progression ralentie. On ne rattrape jamais une séance ratée.

Le vélo / home trainer (0 à 3 séances par semaine, réglage dans *Objectif*) ajoute de l'endurance
sans impact : jours sans course d'abord, jamais la veille d'une séance dure, endurance en zone 2
(56–72 % FTP) et un « sweet spot » (88–93 % FTP) en phase de développement. Cibles en watts si
ta FTP est renseignée, sinon en % de FTP, plus un repère cardio pour rouler dehors. Export `.zwo`
(Zwift…) et `.fit` (montre/compteur Garmin). Les sorties vélo comptent dans ta charge, pas dans
tes kilomètres de course. Douleur au pied, à l'Achille ou au mollet → le prochain footing passe en vélo.

Le renfo pioche dans 20 exercices (sans matériel, élastiques, kettlebell), un par famille
(fessiers, cuisses, mollets, gainage, équilibre), en favorisant tes cœurs et en excluant
tes « bof ».

Ce n'est pas un avis médical : une douleur qui dure se montre à un·e professionnel·le.

---

## Envoyer une séance sur la montre

Garmin ne permet pas aux clés personnelles d'envoyer une séance directement. Deux options :
- **Fichier** : bouton « Télécharger pour la montre », puis copie du fichier `.fit` dans
  `GARMIN/NewFiles` (montre branchée en USB à un ordi).
- **Téléphone** : recopier les étapes dans Garmin Connect › Entraînements › Créer.

Teste d'abord avec une séance : le fichier suit le format officiel FIT, mais chaque
modèle de montre a ses petites manies.

---

## Pour les curieuses et curieux du code

```
app.py                  point d'entrée Streamlit
foulee/engine/          le moteur (sans Streamlit) : vdot, charge, vfc, plan, ajustement, renfo
foulee/data/            Garmin, démo, fichiers FIT/GPX, sauvegarde
foulee/ui/              thème, composants et écrans
assets/exos/            illustrations des exercices
tests/                  python -m pytest
```

## Changer une séance de jour

Onglet **Semaine** → « Changer de jour » sous une séance → choisis le jour → Déplacer. Si une séance du même type est déjà ce jour-là, elles s'échangent. Le bouton en bas remet les jours prévus par le coach.

## Annuler la séance du jour

Aujourd'hui → « Annuler cette séance » → choisis une raison (facultatif). Une séance clé (fractionné, seuil, sortie longue) prend la place d'un footing plus tard dans la semaine si ça ne colle pas deux séances dures ; un footing annulé n'est pas rattrapé. « Malade » ou « Douleur » : pas d'intensité les 3 jours suivants. « Finalement je la fais » annule l'annulation.

## Ta FC pendant les sorties

L'app télécharge le fichier de chaque sortie (Garmin ou Polar), lit ta FC point par point et l'analyse : temps dans chaque zone (Karvonen, à partir de ta FC max et de ta FC repos), dérive cardiaque sur les sorties régulières, footing trop rapide. L'analyse apparaît dans « Comment c'était ? », sous « Voir ma FC pendant la sortie » (Semaine) et dans Forme → « Analyser ma FC sur une sortie ». Le coach en tient compte.

## Ta FC ajuste le plan

Forme → « Mes sorties » : touche n'importe quelle sortie passée pour voir ta FC analysée (« Analyser N sorties » le fait d'un coup). Chaque analyse est gardée, et le coach s'en sert :
- 2 de tes 4 derniers footings trop hauts en FC → allures un peu plus lentes ;
- dérive cardiaque sur 2 sorties longues de suite → la suivante raccourcie de 10 % ;
- FC anormalement haute pour ta vitesse sur la dernière sortie facile → la prochaine séance dure devient un footing ;
- à effort facile, tu vas plus loin par battement qu'il y a un mois → allures un peu plus rapides.
Chaque séance affiche aussi ta FC cible.

## Aperçu des prochaines séances

Semaine → « Aperçu » sous une séance à venir : étapes, allures, FC cible, pourquoi cette séance, fichier pour la montre.
