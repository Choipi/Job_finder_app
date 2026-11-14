# Scorer les offres avec un LLM

Ce document décrit le pipeline de scoring ajouté en phase 6. Il complète
[`llm.md`](llm.md), qui explique le client et la génération de lettres.

## 1. Pourquoi deux étages

Un LLM est cher et lent. Toutes les offres n'ont pas besoin d'être évaluées :

```
Offre
  │
  ├─ pré-filtre déterministe (mots-clés, lieux, remote)
  │     └─ hors critères → score 0, statut "filtered", aucun appel LLM
  │
  └─ appel LLM → JSON { score, reasons, blockers }
        └─ score 0-100, raisons, bloquants, statut "scored"
```

Le pré-filtre est explicable et gratuit. Le LLM juge ce que les règles ne savent
pas faire : pertinence métier, séniorité, cohérence du parcours.

## 2. Schéma de sortie

```json
{
  "score": 87,
  "reasons": [
    "Les compétences Python et Flask correspondent au poste.",
    "Le niveau senior est cohérent avec cinq ans d'expérience.",
    "Le format hybride à Paris correspond aux critères."
  ],
  "blockers": []
}
```

- `score` : entier 0-100.
- `reasons` : 2 à 4 faits vérifiables.
- `blockers` : 0 à 3 bloquants objectifs (lieu, contrat, séniorité).

Le prompt système est dans `backend/app/scoring/prompts/score_system.md` et
versionné par `PROMPT_VERSION = "score/v1"`.

## 3. Ce qui est envoyé au modèle

`build_score_messages()` assemble :

- le profil : nom, poste visé, présentation ;
- les critères de la campagne : mots-clés, lieux, remote, contrats ;
- un extrait du CV (8 000 caractères max) ;
- l'offre : titre, entreprise, lieu, remote, contrat, description (12 000 max).

Les balises `<profil>`, `<criteres>`, `<cv>`, `<offre>` séparent les données des
instructions. L'offre est explicitement une donnée, pas une consigne.

## 4. Pré-filtre

`prefilter_reasons()` dans `backend/app/scoring/service.py` :

- si la campagne a des mots-clés, au moins un doit apparaître dans le titre ou la
  description ;
- si elle a des lieux, l'offre doit correspondre, sauf si la campagne accepte le
  remote et que l'offre est remote ;
- si un mode de travail est imposé, il doit correspondre.

Une offre filtrée reçoit quand même une `OfferScore` avec `status="filtered"`,
un score 0 et la raison. L'interface peut donc expliquer pourquoi elle n'a pas
été évaluée, au lieu de la faire disparaître silencieusement.

## 5. Persistance et audit

Table `offer_score` :

```
offer_id (unique), status, score, reasons, blockers,
model, prompt_version, error, created_at, updated_at
```

`Offer.score` est dénormalisé pour le tri. `LLMCall` journalise l'appel
(`task="scoring"`, tokens, coût, latence, erreur).

Une offre est rescorée si :

- elle n'a pas encore de score ;
- le dernier scoring est en erreur ;
- le modèle ou la version du prompt a changé.

## 6. Coût et latence mesurés

Exemple réel sur une offre Python senior :

```
deepseek-v4.1-flash · 684 tokens entrée + 309 sortie
5,1 s · 0,000288 $ · score 95/100
```

Avec 200 offres, un scoring complet coûte quelques centimes. Le vrai levier est
le pré-filtre et la taille du contexte, pas le prix unitaire.

## 7. Évaluation

Les tests unitaires vérifient le pré-filtre, le parsing JSON et la persistance.
Ils ne mesurent pas la qualité du jugement. Pour l'évaluer :

1. constituer un jeu de 20 à 50 offres annotées manuellement (pertinent / limite /
   hors sujet) ;
2. comparer le score LLM à l'annotation ;
3. mesurer les faux positifs (offres hors sujet bien notées) et les faux négatifs
   (bonnes offres filtrées ou mal notées) ;
4. suivre la calibration : parmi les offres score ≥ 80, combien sont réellement
   pertinentes ?
5. versionner le prompt et le modèle dans chaque ligne `offer_score` ;
6. tester un changement de prompt sur le même jeu avant de le déployer.

Pièges :

- le modèle peut surévaluer une offre qui répète les mots-clés du profil ;
- il peut inventer une correspondance de compétence ;
- les bloquants doivent rester factuels ;
- un score élevé n'est pas une garantie : la relecture humaine reste nécessaire.

## 8. Fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/scoring/prompts/score_system.md` | grille et format JSON |
| `backend/app/scoring/service.py` | pré-filtre, prompt, appel, parsing, persistance |
| `backend/app/models.py` | `OfferScore`, `Offer.score` |
| `backend/app/api/employers.py` | `POST /api/offers/score`, filtres et tri |
| `backend/app/llm/mock.py` | réponse de scoring déterministe pour les tests |
| `frontend/src/pages/OffersPage.vue` | score, raisons, bloquants, actions |
| `frontend/src/stores/offers.ts` | état et appels API |

## 9. Exercices

1. Modifier la grille pour pénaliser explicitement les offres en anglais si le
   candidat ne parle pas anglais.
2. Comparer `deepseek-v4.1-flash` et `claude-haiku-5-5` sur 20 offres : accord,
   coût, latence.
3. Ajouter un score par dimension (compétences, lieu, séniorité) et une moyenne
   pondérée.
4. Re-scorer automatiquement les offres filtrées quand la campagne change.
5. Construire le jeu annoté et calculer la précision à seuil 70.
6. Ajouter un cache par empreinte d'offre et version de prompt.
