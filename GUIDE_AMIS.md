# Ta propre Foulée en 20 minutes

Bienvenue ! Foulée est une app d'entraînement course à pied connectée à Garmin.
Tu vas créer **ta propre copie** : ton app, ta clé Garmin, tes données. Personne d'autre
n'y a accès, pas même la personne qui t'a envoyé ce guide. C'est gratuit.

**Il te faut :** une montre Garmin ou Polar, un ordinateur pour l'installation (ensuite tout
se passe sur le téléphone), environ 20 minutes.

---

### Étape 1 · Ta clé Garmin (2 min) · *si tu as une Polar, va à la section Polar en bas*
1. Sur un ordinateur, va sur **connect.garmin.com** et connecte-toi.
2. **Paramètres › Personal API Token › Créer une clé**. Accepte les conditions,
   choisis **1 an**.
3. Copie la clé dans une note : Garmin ne l'affiche **qu'une seule fois**.

### Étape 2 · Ta copie du code (3 min)
1. Crée un compte sur **github.com**.
2. Ouvre le lien du dépôt Foulée qu'on t'a envoyé, puis clique **Fork** (en haut à droite) › **Create fork**.

### Étape 3 · Ta sauvegarde (5 min)
1. Crée un compte sur **supabase.com** › **New project** (nom : foulee, région : Europe,
   mot de passe : génère-le, tu n'en auras pas besoin).
2. Menu **SQL Editor › New query**. Colle ce texte, puis clique **Run** :
   ```sql
   create table if not exists public.foulee (
     cle text primary key, valeur jsonb not null, maj timestamptz not null default now());
   alter table public.foulee enable row level security;
   grant select, insert, update, delete on table public.foulee to service_role;
   ```
   (À la création du projet, laisse « Enable Data API » coché et « Automatically expose new tables » décoché.)
3. **Project Settings › API Keys** : copie l'**URL du projet** et la **clé secrète**
   (elle commence par `sb_secret_`).

### Étape 4 · Ton app en ligne (5 min)
1. Va sur **share.streamlit.io** › *Continue with GitHub*.
2. **Create app** › choisis ton dépôt `foulee` › Main file : `app.py`.
3. **Advanced settings › Secrets**, colle en remplaçant par tes valeurs :
   ```toml
   GARMIN_API_KEY = "ta-cle-garmin"
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "sb_secret_xxxx"
   APP_PASSWORD = "invente-un-mot-de-passe"
   ```
4. **Deploy**. Patiente 2 minutes : l'app s'ouvre.

### Étape 5 · Sur ton iPhone (1 min)
Ouvre le lien de ton app dans **Safari** › **Partager** › **Sur l'écran d'accueil**.
Entre ton mot de passe, puis laisse-toi guider : l'app lit tes 6 derniers mois et te propose un plan.

---

### Section Polar (à la place des étapes 1 et 4.3)
1. Fais d'abord les étapes 2, 3 et 4 jusqu'au Deploy, avec ces secrets (sans clé Garmin) :
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "sb_secret_xxxx"
   APP_PASSWORD = "invente-un-mot-de-passe"
   ```
   Note l'adresse de ton app (par exemple `https://ton-app.streamlit.app`).
2. Sur **admin.polaraccesslink.com**, connecte-toi avec ton compte Polar Flow et crée un client.
   Lien de retour (*redirect URL*) : l'adresse de ton app **suivie d'un /**.
3. Ajoute dans les *Secrets* de Streamlit :
   ```toml
   POLAR_CLIENT_ID = "ton-client-id"
   POLAR_CLIENT_SECRET = "ton-client-secret"
   APP_URL = "https://ton-app.streamlit.app"
   ```
4. Dans l'app : choisis **Polar** › **Connecter mon compte Polar** › accepte.

Polar ne donne que tes 30 derniers jours : l'app part de là et garde tout ensuite.
Ouvre-la au moins une fois par mois pour ne rien perdre.

### Recevoir les nouveautés
Quand une nouvelle version sort : sur la page GitHub de ta copie, clique **Sync fork ›
Update branch**. Ton app se met à jour toute seule, et tes données ne bougent pas.

### Questions fréquentes
- **« Garmin refuse la clé »** : elle a expiré (au bout d'un an). Crée-en une nouvelle et
  remplace-la dans les *Secrets* de Streamlit.
- **L'app affiche « Your app is sleeping »** : sans visite pendant 12 h, elle s'endort. Clique sur
  le bouton pour la réveiller (30 secondes).
- **Mes données sont-elles visibles ?** Ton code est public, tes données non : elles sont
  dans ta base Supabase, protégée par ta clé secrète, et l'app demande ton mot de passe.
- **Envoyer une séance sur la montre ?** Bouton « Télécharger pour la montre », puis copie
  du fichier dans `GARMIN/NewFiles` (montre en USB), ou recopie des étapes dans Garmin Connect.
