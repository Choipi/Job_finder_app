# Job Finder

Application locale de veille d'offres d'emploi : collecte multi-sources, scoring des
offres par LLM, puis génération de lettres de motivation à partir d'un CV et d'une
lettre type.

Le projet est aussi un support d'apprentissage : les étapes qui utilisent un LLM
( scoring et rédaction ) sont isolées dans des modules dédiés, avec des prompts en
fichiers séparés et un client mockable pour les tests.

## État actuel — phase 1 terminée

- [x] Socle Flask : factory, configuration centralisée, CORS, erreurs JSON
- [x] `GET /api/health` : état du service, modèles configurés, aucune fuite de clé
- [x] Front Vue 3 + Vite + TypeScript + Tailwind + Pinia + Vue Router
- [x] Tableau de bord connecté à l'API, pages de la feuille de route
- [x] 5 tests backend

Prochaines phases : profil et campagne, client LLM et lettres, connecteurs,
scoring, interface des offres.

## Stack

| Couche | Choix |
|---|---|
| Front | Vue 3, Vite 6, TypeScript, Tailwind 3, Pinia, Vue Router |
| Back | Python 3.11, Flask 3, SQLite (phase 2) |
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
make test    # pytest, 5 tests
make build   # vue-tsc + build de production
```

## Structure

```
backend/
  app/
    __init__.py        # factory Flask + gestion d'erreurs JSON
    config.py          # lecture unique des variables d'environnement
    api/               # blueprints, routes /api
  tests/               # pytest + client de test Flask
  run.py               # point d'entrée de développement
frontend/
  src/
    api/               # client fetch typé, types de l'API
    components/        # briques d'interface réutilisables
    pages/             # une page par route
    router/            # routes et métadonnées
    stores/            # état Pinia
.env.example           # toutes les variables, valeurs vides
```

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

### Sécurité de la clé

- La clé vit dans `.env`, ignoré par Git ; seul `.env.example` est versionné.
- Le navigateur ne la reçoit jamais : `/api/health` expose uniquement
  `llm.configured`, un booléen.
- Ne jamais journaliser la configuration complète ni la renvoyer dans une erreur.

## Feuille de route

1. **Socle** — fait.
2. **Profil & campagne** — CV PDF, lettre type, critères, durée.
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
