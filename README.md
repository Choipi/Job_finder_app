# Job Finder

Application locale de veille d'offres d'emploi : collecte multi-sources, scoring des
offres par LLM, puis génération de lettres de motivation à partir d'un CV et d'une
lettre type.

Le projet est aussi un support d'apprentissage : les étapes qui utilisent un LLM
( scoring et rédaction ) sont isolées dans des modules dédiés, avec des prompts en
fichiers séparés et un client mockable pour les tests.

## État actuel — phases 1 à 4 terminées

- [x] Socle Flask : factory, configuration centralisée, CORS, erreurs JSON
- [x] `GET /api/health` : état du service, modèles configurés, aucune fuite de clé
- [x] Front Vue 3 + Vite + TypeScript + Tailwind + Pinia + Vue Router
- [x] SQLite via SQLAlchemy, création automatique du schéma au démarrage
- [x] Profil : identité, présentation, CV, lettre type
- [x] Import du CV en PDF, extraction du texte, correction manuelle
- [x] Campagne : critères, sources, période, fréquence, seuil d'affichage
- [x] Client LLM OpenCode Go : retries, timeout, JSON mode, coût, télémétrie
- [x] Génération de lettres, sortie éditable, historique, suppression
- [x] Sélection des modèles et test de connexion dans les Réglages
- [x] Watchlist de 200 employeurs IA, découverte d'ATS, collecte directe
- [x] Adaptateurs Ashby, Greenhouse, Lever, SmartRecruiters, Workable
- [x] Offres normalisées, dédupliquées, avec lien de candidature employeur
- [x] 60 tests backend (profil, CV, campagne, LLM, lettres, ATS, employeurs)

Prochaines phases : job boards en complément, scoring LLM, scheduler, interface avancée.

> Guides : [`docs/llm.md`](docs/llm.md) pour les appels LLM, [`docs/employers.md`](docs/employers.md) pour la collecte employeurs.

## Stack

| Couche | Choix |
|---|---|
| Front | Vue 3, Vite 6, TypeScript, Tailwind 3, Pinia, Vue Router |
| Back | Python 3.11, Flask 3, SQLAlchemy 2, SQLite |
| LLM | OpenCode Go, via une API compatible OpenAI, client httpx |
| Collecte | APIs officielles puis scraping ciblé (requests/Playwright) |

## Prérequis

- Python 3.11+
- Node.js 18.19+ (testé avec 18.19)
- npm 9+

## Installation

```bash
cp .env.example .env      # puis remplir OPENCODE_BASE_URL et OPENCODE_API_KEY
make install              # venv Python + dépendances npm
```

Sans `make` :

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

cd ../frontend
npm install
```

## Lancer l'application

Deux terminaux, ou `make backend` et `make frontend`.

```bash
# Terminal 1 — API sur http://127.0.0.1:5000
make backend

# Terminal 2 — interface sur http://127.0.0.1:5173
make frontend
```

Vite proxifie `/api` vers Flask : le navigateur n'appelle jamais directement le
backend et aucune origine supplémentaire n'est nécessaire en développement.

Vérifications rapides :

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5173/api/health   # via le proxy Vite
```

## Tests et build

```bash
make test    # pytest, 60 tests
make build   # vue-tsc + build de production
```

## API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | état du service, sans secret |
| GET / PUT | `/api/profile` | lire / enregistrer le profil |
| POST / DELETE | `/api/profile/cv` | importer un CV PDF / le supprimer |
| GET / PUT | `/api/campaign` | lire / enregistrer la campagne |
| PUT | `/api/campaign/models` | choisir les modèles de scoring et de rédaction |
| GET | `/api/sources` | catalogue des 7 sources |
| GET / POST | `/api/letters` | historique / générer une lettre |
| GET / PUT / DELETE | `/api/letters/<id>` | lire / modifier / supprimer |
| GET | `/api/models` | catalogue des modèles et tarifs |
| POST | `/api/llm/test` | test de connexion clé + endpoint + modèle |
| GET | `/api/llm/usage` | tokens, coût estimé et derniers appels |
| GET / POST | `/api/employers` | watchlist / ajouter un employeur |
| PATCH | `/api/employers/<id>` | activer, renommer, changer l'URL carrières |
| POST | `/api/employers/seed` | charger la watchlist IA France (200) |
| POST | `/api/employers/discover` | détecter les ATS par lot |
| POST | `/api/employers/collect` | collecter les offres par lot |
| POST | `/api/employers/<id>/collect` | collecter un employeur |
| GET | `/api/offers` | offres collectées, filtre campagne optionnel |

Les erreurs de validation renvoient `400` avec un objet `fields` :

```json
{
  "error": {
    "code": 400,
    "name": "Validation Error",
    "message": "Certains champs sont invalides.",
    "fields": { "ends_on": "La date de fin doit être postérieure à la date de début." }
  }
}
```

Le front s'en sert pour afficher les messages sous les bons champs.

## Structure

```
backend/
  app/
    __init__.py        # factory Flask, stockage, gestion d'erreurs JSON
    config.py          # lecture unique des variables d'environnement
    extensions.py      # instance SQLAlchemy partagée
    models.py          # Profile et Campaign (singletons)
    serializers.py     # sortie JSON explicite, sans chemin de fichier
    validation.py      # nettoyage et collecte d'erreurs par champ
    sources.py         # catalogue des sources
    services/cv.py     # stockage du PDF + extraction pypdf
    llm/               # client OpenCode Go, mock, catalogue, télémétrie
    letters/           # prompt versionné + orchestration de génération
    employers/         # watchlist, seed IA France, découverte ATS
    collectors/ats/    # adaptateurs Ashby, Greenhouse, Lever, etc.
    api/               # blueprints health, profile, campaign, letters, llm, employers
  tests/               # 47 tests, dont client HTTP simulé et PDF générés
  run.py
frontend/
  src/
    api/               # client fetch typé, types de l'API
    components/        # FormSection, TagInput, StatusPill…
    pages/             # Dashboard, Offres, Lettres, Profil, Campagne, Réglages
    stores/            # health, profile, campaign
    router/
.env.example           # toutes les variables, valeurs vides
```

## Données locales

- Base : `backend/instance/job_finder.db`
- CV importés : `backend/uploads/cv/`
- Ces deux dossiers sont ignorés par Git.

Pour repartir de zéro, arrêter Flask puis supprimer `backend/instance/job_finder.db`
et `backend/uploads/cv/`. Le schéma et la campagne par défaut sont recréés au
prochain démarrage.

### Watchlist employeurs

La watchlist de test (200 employeurs IA en France, dont 17 ATS vérifiés) est
chargée depuis l'interface **Employeurs**, ou en CLI :

```bash
cd backend
flask --app run:app employers-seed
flask --app run:app employers-discover --limit 10
flask --app run:app employers-collect --limit 5 --max-offers 50
```

Aucune clé API n'est nécessaire pour les ATS : ce sont des endpoints publics.

## Configuration

Toutes les variables sont documentées dans `.env.example`. Les principales :

| Variable | Rôle |
|---|---|
| `OPENCODE_BASE_URL` | URL de base OpenAI-compatible, sans slash final |
| `OPENCODE_API_KEY` | clé personnelle, jamais versionnée |
| `SCORING_MODEL` | modèle chargé de noter les offres |
| `LETTER_MODEL` | modèle chargé de rédiger les lettres |
| `MAX_SCORING_PER_SCAN` | garde-fou du nombre d'appels LLM par scan |
| `LLM_PROVIDER` | `opencode_go` (réel) ou `mock` (simulé) |
| `LLM_TIMEOUT_SECONDS` | délai maximal d'un appel |
| `LLM_MAX_RETRIES` | nombre de tentatives supplémentaires |
| `LLM_TEMPERATURE_LETTER` | créativité de la rédaction |
| `CORS_ORIGINS` | origines autorisées, séparées par des virgules |
| `DATABASE_URL` | vide = SQLite dans `backend/instance/` |
| `UPLOAD_DIR` | vide = `backend/uploads/` |

### Sécurité de la clé

- La clé vit dans `.env`, ignoré par Git ; seul `.env.example` est versionné.
- Le navigateur ne la reçoit jamais : `/api/health` expose uniquement
  `llm.configured` et `llm.ready`, des booléens.
- Ne jamais journaliser la configuration complète ni la renvoyer dans une erreur.

### Développer sans clé

```bash
LLM_PROVIDER=mock make backend
```

Le client simulé renvoie une lettre déterministe et alimente quand même
l'historique et la télémétrie.

## Feuille de route

1. **Socle** — fait.
2. **Profil & campagne** — fait.
3. **LLM & lettres** — fait.
4. **Employeurs & ATS** — fait : watchlist, découverte, collecte directe.
5. **Job boards & APIs** — WTTJ sitemap, Adzuna et Jooble en complément.
6. **Scoring & scheduler** — déduplication avancée, pré-filtre, scoring, scans planifiés.
7. **Interface offres avancée** — score, suppressions, lettres, statuts.

## Collecte : règles assumées

Le scraping de sites comme Indeed ou LinkedIn est contraire à leurs conditions
d'utilisation et peut entraîner un blocage. Le projet est prévu pour un usage
personnel, local, à faible volume :

- `robots.txt` respecté, délais aléatoires, faible parallélisme par domaine ;
- un connecteur par source, isolé et désactivable en un clic ;
- les APIs officielles sont privilégiées quand elles existent ;
- aucune redistribution des annonces collectées.

## Licence

Apache 2.0, voir `LICENSE`.
