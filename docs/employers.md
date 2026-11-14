# Collecter les offres directement chez les employeurs

Ce document explique la couche « employeurs » ajoutée en phase 4 : pourquoi elle
existe, comment elle fonctionne, et comment l'étendre.

## 1. Pourquoi les ATS plutôt que les job boards

Un grand nombre d'employeurs publient leurs offres via un **ATS** (Applicant
Tracking System) : Greenhouse, Lever, Ashby, SmartRecruiters, Workable, etc.
Ces plateformes exposent presque toujours une **API JSON publique** :

- données structurées (titre, lieu, contrat, description) ;
- lien de candidature d'origine, sur le site de l'employeur ;
- pas de HTML à parser, pas de captcha ;
- stabilité bien meilleure qu'un scraper.

À l'inverse, les job boards sont protégés : WTTJ renvoie `202` avec un corps vide
après quelques requêtes, HelloWork est derrière Cloudflare, APEC derrière
DataDome, Indeed renvoie `403`, et LinkedIn interdit l'automatisation dans ses
CGU. Le scraping des job boards reste possible avec un navigateur, mais il est
fragile et souvent contraire aux conditions d'utilisation.

## 2. Le modèle « watchlist »

On ne peut pas crawler « tous les sites d'employeurs de France ». On suit donc une
**liste d'employeurs** :

- watchlist de test : **200 entreprises IA en France** ;
- **17 ATS vérifiés manuellement** au départ ;
- les 183 autres passent par la découverte (page carrière puis slugs testés) ;
- l'utilisateur peut ajouter une entreprise à tout moment.

Pour une campagne, le secteur et la zone ne sont pas codés en dur : les
**mots-clés, lieux et mode de télétravail de la campagne** filtrent les offres
collectées. La watchlist n'est que le pool d'employeurs à interroger.

## 3. Flux de collecte

```
EmployerSource (domaine, ATS, slug)
  → adaptateur ATS (Ashby, Greenhouse, Lever, SmartRecruiters, Workable)
  → CollectedOffer normalisé
  → empreinte (titre | entreprise | lieu)
  → INSERT ou mise à jour dans Offer
  → filtre campagne à la lecture (mots-clés, lieux, remote)
```

Le lien `apply_url` est conservé tel que fourni par l'ATS : c'est le lien de
candidature de l'employeur, pas un lien d'agrégateur.

## 4. Découverte d'un ATS

Trois stratégies, dans cet ordre :

1. **URL déjà connue** : si `careers_url` pointe vers `jobs.ashbyhq.com/mistral.ai`,
   on lit le slug directement.
2. **Page carrière** : on récupère la page d'accueil et quelques chemins courants
   (`/careers`, `/jobs`, `/carrieres`, `/nous-rejoindre`…) puis on cherche un lien
   ATS dans le HTML. C'est ainsi que Mistral AI est détecté.
3. **Sondes de slugs** : on teste quelques variantes (`mistral.ai`, `mistral`,
   `mistralai`) sur les API. Limité à quelques requêtes par employeur.

Piège rencontré : SmartRecruiters renvoie `200` avec `totalFound: 0` pour un slug
inexistant. La sonde exige donc `totalFound > 0`, sinon Hugging Face et Mistral
seraient de faux positifs.

## 5. Adaptateurs disponibles

| ATS | Endpoint public | Remarque |
|---|---|---|
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | descriptions complètes, `applyUrl` |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | contenu HTML échappé |
| Lever | `api.lever.co/v0/postings/{slug}?mode=json` | dates en millisecondes |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings` | description via endpoint détail |
| Workable | `apply.workable.com/api/v1/widget/accounts/{slug}?details=true` | `telecommuting`, `application_url` |

Ajouter un ATS = un fichier dans `backend/app/collectors/ats/` avec :

```python
NAME = "mon_ats"
def detect_url(url: str) -> str | None: ...
def fetch(client, slug, *, limit=100) -> list[CollectedOffer]: ...
def probe(client, slug) -> bool: ...
```

Puis l'ajouter dans `collectors/ats/__init__.py`.

## 6. Fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/models.py` | `EmployerSource`, `Offer` |
| `backend/app/employers/seed_ai_france.json` | watchlist de 200 employeurs IA |
| `backend/app/employers/service.py` | seed, collecte, empreinte, déduplication |
| `backend/app/employers/detection.py` | URL, page carrière, sondes de slugs |
| `backend/app/collectors/ats/base.py` | normalisation HTML, dates, remote, client HTTP |
| `backend/app/collectors/ats/*.py` | un adaptateur par ATS |
| `backend/app/api/employers.py` | API watchlist, collecte, offres |
| `backend/app/cli.py` | commandes Flask |
| `frontend/src/pages/EmployersPage.vue` | gestion de la watchlist |
| `frontend/src/pages/OffersPage.vue` | offres collectées et filtre campagne |

## 7. Ajout manuel d'une offre

Une annonce trouvée hors ATS peut être ajoutée depuis **Offres → Ajouter une
offre** :

- intitulé, entreprise, lieu, lien, contrat, remote, texte complet ;
- empreinte `titre + entreprise + lieu` : une offre identique n'est pas dupliquée ;
- une offre précédemment supprimée est restaurée et retirée de la blacklist ;
- l'offre est immédiatement disponible pour le scoring et la lettre ;
- le bouton **Ajouter et rédiger la lettre** ouvre directement l'éditeur avec
  l'offre préremplie.

L'ajout manuel désactive le filtre campagne dans l'interface pour que l'offre
reste visible, même si ses mots-clés ne correspondent pas encore.

## 8. Commandes

```bash
cd backend
flask --app run:app employers-seed
flask --app run:app employers-discover --limit 10
flask --app run:app employers-collect --limit 5 --max-offers 50
```

Ou depuis l'interface : **Employeurs → Détecter 8 ATS / Collecter 5 employeurs**.

## 9. Limites et choix assumés

- **Couverture partielle** : on couvre les employeurs de la watchlist, pas tout le
  marché. Les PME sans ATS restent invisibles.
- **Découverte imparfaite** : un site rendu en JavaScript peut cacher son lien ATS.
  Playwright sera ajouté en phase 5 pour ces cas.
- **Déduplication simple** : l'empreinte titre + entreprise + lieu peut fusionner
  deux offres réellement distinctes. À raffiner avec l'URL et le département.
- **Pas de scoring ici** : la collecte stocke, le filtre campagne est un simple
  `LIKE` sur les mots-clés et lieux. Le scoring LLM arrive en phase 6.
- **Volume** : 200 employeurs peuvent produire plusieurs milliers d'offres. On
  collecte par petits lots, avec un plafond d'offres par employeur.
- **Légal** : les API ATS sont publiques et prévues pour être consommées. On
  respecte les délais, on s'identifie, et on ne contourne pas les protections des
  job boards.

## 10. Exercices

1. Ajouter l'adaptateur Recruitee ou Teamtailor.
2. Améliorer la déduplication avec le couple `(entreprise, titre, ville)` +
   normalisation des accents.
3. Ajouter un filtre de contrat fiable en mappant les libellés ATS vers CDI/CDD.
4. Lancer la détection sur les 183 employeurs restants et mesurer le taux d'ATS
   trouvés par secteur.
5. Comparer le nombre d'offres collectées par ATS et le temps de collecte.
6. Ajouter un `sitemap` WTTJ comme source de découverte d'employeurs, sans
   scraper les pages de recherche.
