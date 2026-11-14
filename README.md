# Job Finder

Application locale de veille d'offres d'emploi : collecte multi-sources, scoring des
offres par LLM, puis génération de lettres de motivation à partir d'un CV et d'une
lettre type.

Le projet est aussi un support d'apprentissage : les étapes qui utilisent un LLM
( scoring et rédaction ) sont isolées dans des modules dédiés, avec des prompts en
fichiers séparés et un client mockable pour les tests.

## État actuel — phases 1 et 2 terminées

- [x] Socle Flask : factory, configuration centralisée, CORS, erreurs JSON
- [x] `GET /api/health` : état du service, modèles configurés, aucune fuite de clé
- [x] Front Vue 3 + Vite + TypeScript + Tailwind + Pinia + Vue Router
- [x] SQLite via SQLAlchemy, création automatique du schéma au démarrage
- [x] Profil : identité, présentation, CV, lettre type
- [x] Import du CV en PDF, extraction du texte, correction manuelle
- [x] Campagne : critères, sources, période, fréquence, seuil d'affichage
- [x] 22 tests backend (profil, CV, campagne, health)

Prochaines phases : client LLM et lettres, connecteurs, scoring, interface des offres.

## Stack

| Couche | Choix |
|---|---|
| Front | Vue 3, Vite 6, TypeScript, Tailwind 3, Pinia, Vue Router |
| Back | Python 3.11, Flask 3, SQLAlchemy 2, SQLite |
| LLM | OpenCode Go, via une API compatible OpenAI |
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
make test    # pytest, 22 tests
make build   # vue-tsc + build de production
```

## API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | état du service, sans secret |
| GET / PUT | `/api/profile` | lire / enregistrer le profil |
| POST / DELETE | `/api/profile/cv` | importer un CV PDF / le supprimer |
| GET / PUT | `/api/campaign` | lire / enregistrer la campagne |
| GET | `/api/sources` | catalogue des 7 sources |

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
    api/               # blueprints health, profile, campaign
  tests/               # 22 tests, dont génération de PDF pour l'extraction
  run.py
frontend/
  src/
    api/               # client fetch typé, types de l'API
    components/        # FormSection, TagInput, StatusPill…
    pages/             # Profil, Campagne, Offres, Réglages, Dashboard
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

## Configuration

Toutes les variables sont documentées dans `.env.example`. Les principales :

| Variable | Rôle |
|---|---|
| `OPENCODE_BASE_URL` | URL de base OpenAI-compatible, sans slash final |
| `OPENCODE_API_KEY` | clé personnelle, jamais versionnée |
| `SCORING_MODEL` | modèle chargé de noter les offres |
| `LETTER_MODEL` | modèle chargé de rédiger les lettres |
| `MAX_SCORING_PER_SCAN` | garde-fou du nombre d'appels LLM par scan |
| `CORS_ORIGINS` | origines autorisées, séparées par des virgules |
| `DATABASE_URL` | vide = SQLite dans `backend/instance/` |
| `UPLOAD_DIR` | vide = `backend/uploads/` |

### Sécurité de la clé

- La clé vit dans `.env`, ignoré par Git ; seul `.env.example` est versionné.
- Le navigateur ne la reçoit jamais : `/api/health` expose uniquement
  `llm.configured`, un booléen.
- Ne jamais journaliser la configuration complète ni la renvoyer dans une erreur.

## Feuille de route

1. **Socle** — fait.
2. **Profil & campagne** — fait.
3. **LLM & lettres** — client OpenCode Go, modèles, génération éditable.
4. **Connecteurs APIs** — France Travail, Adzuna, Welcome to the Jungle.
5. **Scrapers** — HelloWork, APEC, Indeed, LinkedIn.
6. **Scoring & scheduler** — déduplication, pré-filtre, scoring, scans planifiés.
7. **Interface offres** — cartes, filtres, trois actions, statuts.

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
