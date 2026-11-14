# Architecture du projet

Job Finder est une application locale mono-utilisateur : Vue 3 pour l'interface,
Flask pour l'API et les traitements, SQLite pour les données.

## 1. Vue d'ensemble

```
Vue 3 (Vite, 5173)
  │  /api (proxy Vite)
Flask (5000)
  ├─ API REST
  ├─ Profil / campagne
  ├─ Collecte employeurs (ATS publics)
  ├─ Scoring LLM
  ├─ Génération de lettres
  ├─ Scheduler APScheduler
  └─ SQLite + uploads CV
```

## 2. Flux principaux

### Collecte

```
Campagne (critères)
  → watchlist d'employeurs
  → adaptateur ATS (Ashby, Greenhouse, Lever, SmartRecruiters, Workable)
  → normalisation + empreinte
  → Offer (dédupliquée, lien employeur)
```

### Scoring

```
Offer
  → pré-filtre règles (mots-clés, lieux, remote)
  → offre filtrée : OfferScore(status=filtered)
  → sinon LLM → OfferScore(status=scored, score, raisons, bloquants)
  → Offer.score dénormalisé pour le tri
```

### Lettre

```
Offre (collectée ou ajoutée manuellement) + Profil (CV, lettre type)
  → prompt système versionné
  → OpenCode Go
  → JSON { subject, body }
  → GeneratedLetter (offer_id optionnel) + LLMCall
```

### Scan

```
Scheduler / bouton manuel
  → collecte un lot d'employeurs
  → score un lot d'offres
  → ScanRun (audit)
  → Campaign.last_scan_at
```

## 3. Modèle de données

| Table | Rôle |
|---|---|
| `profile` | profil, CV texte, lettre type (singleton) |
| `campaign` | critères, durée, sources, modèles (singleton) |
| `employer_source` | watchlist, ATS détecté, état |
| `offer` | offre normalisée, empreinte, score, statut |
| `offer_score` | dernier jugement LLM (raisons, bloquants, version) |
| `offer_blacklist` | empreintes supprimées définitivement |
| `generated_letter` | lettre générée, liée ou non à une offre |
| `llm_call` | télémétrie de chaque appel LLM |
| `scan_run` | historique des scans |

## 4. Décisions structurantes

- **ATS d'abord** : les offres viennent des employeurs, pas des job boards
  bloqués. Les liens de candidature sont ceux de l'employeur.
- **Scraping seulement où c'est autorisé** : robots.txt et CGU respectés.
- **Deux étages de scoring** : règles déterministes puis LLM, pour maîtriser
  coût et latence.
- **Tout est auditable** : version de prompt, modèle, tokens, coût, erreurs.
- **La clé LLM reste côté serveur** : le navigateur ne reçoit que des booléens.
- **SQLite et create_all** : adapté à un usage local ; une migration SQLite
  minimale ajoute les nouvelles colonnes.

## 5. Limites connues

- La couverture employeurs dépend de la watchlist (200 en test).
- Les job boards (WTTJ, HelloWork, APEC, Indeed, LinkedIn) sont bloqués ou
  interdits ; ils ne sont pas branchés.
- La déduplication par titre + entreprise + lieu peut fusionner deux offres.
- Le scheduler tourne dans le processus Flask : pour un usage intensif, un
  worker séparé serait préférable.
- Le scoring dépend de la qualité du profil et du CV fournis.

## 6. Documentation

- [`llm.md`](llm.md) : client LLM, prompts, retries, coûts.
- [`scoring.md`](scoring.md) : pré-filtre, grille, évaluation.
- [`employers.md`](employers.md) : ATS, watchlist, détection, collecte.
