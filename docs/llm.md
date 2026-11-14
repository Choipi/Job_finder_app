# Utiliser un LLM dans une application

Ce document explique l'implémentation réelle des appels de modèles dans Job Finder.
Il s'adresse à quelqu'un qui connaît déjà le machine learning : l'objectif n'est pas
d'expliquer ce qu'est un transformer, mais comment on **intègre** un modèle
pré-entraîné dans une application fiable, observable et évaluable.

## 1. Ce que fait — et ne fait pas — le LLM ici

- Aucun entraînement, aucun fine-tuning : on utilise un modèle servi par API.
- Le modèle est traité comme une **fonction non déterministe, payante et lente** :
  entrée = messages + paramètres, sortie = texte + tokens consommés.
- Deux tâches prévues : la rédaction de lettres (implémentée) et le scoring des
  offres (phase 6). Les deux partagent le même client et la même télémétrie.

Conséquence de conception : tout ce qui peut être déterministe (validation,
déduplication, filtres, stockage) reste hors du LLM. Le LLM ne fait que ce que
les règles ne savent pas faire : comprendre un texte et rédiger.

## 2. Flux complet d'une génération de lettre

```
Vue (page Lettres)
  │  POST /api/letters
  ▼
Flask — app/api/letters.py
  │  1. validation du payload (app/validation.py)
  │  2. lecture du profil et du CV (SQLite)
  │  3. construction du prompt (app/letters/service.py)
  ▼
app/llm/factory.py ──► app/llm/opencode_go.py
  │  POST https://opencode.ai/inference/go/openai/v1/chat/completions
  ▼
Réponse JSON du fournisseur
  │  4. parsing tolérant du JSON (parse_letter)
  │  5. sauvegarde GeneratedLetter + LLMCall
  ▼
201 { letter, usage, context_truncated }
```

### Carte des fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/llm/client.py` | interface `LLMClient`, `LLMMessage`, `LLMResult` |
| `backend/app/llm/opencode_go.py` | client HTTP réel : headers, retries, timeout, coût |
| `backend/app/llm/mock.py` | client déterministe pour les tests et le mode démo |
| `backend/app/llm/factory.py` | choisit le client selon `LLM_PROVIDER` |
| `backend/app/llm/catalog.py` | catalogue des modèles, prix, capacités, estimation de coût |
| `backend/app/llm/errors.py` | erreurs 502 / 503 / 504 |
| `backend/app/llm/telemetry.py` | une ligne `llm_call` par appel |
| `backend/app/letters/prompts/letter_system.md` | prompt système versionné |
| `backend/app/letters/service.py` | assemblage du contexte, appel, parsing, persistance |
| `backend/app/api/letters.py` | routes HTTP des lettres |
| `backend/app/api/llm.py` | catalogue, test de connexion, consommation |
| `backend/app/models.py` | tables `generated_letter` et `llm_call` |
| `frontend/src/pages/LettersPage.vue` | formulaire, résultat éditable, historique |
| `frontend/src/pages/SettingsPage.vue` | modèles, test, consommation |
| `frontend/src/stores/letters.ts` | état et appels API côté Vue |

## 3. Anatomie d'un appel

```http
POST /inference/go/openai/v1/chat/completions
Authorization: Bearer <OPENCODE_API_KEY>
Content-Type: application/json
User-Agent: job-finder/0.1
x-opencode-session: job-finder-local
```

```json
{
  "model": "claude-haiku-5-5",
  "messages": [
    { "role": "system", "content": "Règles de rédaction…" },
    { "role": "user", "content": "<profil>…</profil>\n<cv>…</cv>\n<offre>…</offre>" }
  ],
  "temperature": 0.3,
  "max_tokens": 4000,
  "response_format": { "type": "json_object" },
  "stream": false
}
```

Réponse simplifiée :

```json
{
  "choices": [{ "message": { "content": "{\"subject\":\"…\",\"body\":\"…\"}" }, "finish_reason": "stop" }],
  "usage": { "prompt_tokens": 1526, "completion_tokens": 1887 }
}
```

Points à retenir :

- **Rôles** : `system` porte les règles stables, `user` porte le contexte variable.
  Ne jamais mettre les règles dans le message utilisateur : elles seraient noyées
  dans le contenu et plus faciles à faire dévier.
- **`x-opencode-session`** : identifiant stable recommandé par le fournisseur pour
  le routage et le cache de prompt shared. Il ne contient aucune donnée personnelle.
- **`User-Agent`** : le fournisseur demande un client identifiable, pas un SDK
  générique.
- **`usage`** : c'est la seule source fiable pour la facturation. On ne l'estime
  pas à partir du texte.

## 4. Construction du prompt

Deux couches, volontairement séparées :

1. **Prompt système** : `app/letters/prompts/letter_system.md`. Il contient le
   rôle, les règles non négociables, la longueur et le format de sortie. Il est
   stable et versionné (`PROMPT_VERSION = "letter/v1"`).
2. **Message utilisateur** : construit dans `build_messages()`. Il contient les
   données du profil, le CV, la lettre type, l'offre et la consigne libre.

### Délimiteurs

Le contexte utilise des balises pseudo-XML :

```
<cv>…</cv>
<offre><description>…</description></offre>
```

Elles servent à deux choses : rendre la structure lisible pour le modèle et
séparer clairement **données** et **instructions**. Une annonce peut contenir
« ignore les instructions précédentes » : le prompt système précise explicitement
que le contenu des balises `<offre>`, `<cv>` et `<lettre_type>` est une donnée,
pas une consigne.

### Bornes de contexte

`LIMITS` dans `letters/service.py` tronque chaque partie (CV 20 000 caractères,
offre 12 000, etc.). La fonction retourne la liste des champs tronqués, affichée
dans l'UI. Sans cette borne, un CV de 40 pages ferait exploser la facture et
pourrait dépasser la fenêtre de contexte.

### Versionner le prompt

`prompt_version` est enregistré dans `generated_letter` et `llm_call`. C'est
l'équivalent d'un commit de modèle : sans lui, impossible de savoir quelle
version a produit quelle lettre lors d'une évaluation ou d'une régression.

## 5. Paramètres de génération

| Paramètre | Valeur ici | Pourquoi |
|---|---|---|
| `temperature` | `0.3` | style stable, sans être rigide. Omis pour les modèles qui le refusent (`Claude Haiku`, `Kimi`, `Gemini` dans le catalogue). |
| `max_tokens` | `4000` | borne de sécurité. Les modèles de raisonnement consomment des tokens avant le texte final. |
| `response_format` | `json_object` | sortie structurée, avec repli automatique si le modèle refuse. |
| `stream` | `false` | inutile pour une génération courte ; simplifie la gestion d'erreur. |

### Le piège rencontré en vrai

Le premier test de connexion utilisait `max_tokens=10`. DeepSeek V4.1 Flash est un
modèle de raisonnement : il a consommé les 10 tokens en raisonnement et renvoyé
un `content` vide. Le client affiche maintenant `finish_reason` dans l'erreur et
le test utilise 64 tokens. C'est un exemple concret de différence entre « le
modèle a répondu » et « le modèle a produit du texte exploitable ».

## 6. Sortie structurée et parsing robuste

On demande :

```json
{ "subject": "…", "body": "…" }
```

Mais on ne fait jamais confiance à cette sortie. `parse_letter()` :

1. retire les fences Markdown ```json ;
2. tente `json.loads` sur le texte complet ;
3. sinon, isole la première `{` et la dernière `}` et réessaie ;
4. sinon, log un avertissement et utilise le texte brut comme corps.

Le repli garde la fonctionnalité utilisable ; le log permet d'améliorer le prompt.
En production, on ajouterait un validateur de schéma (Pydantic) et un compteur de
taux d'échec de parsing.

## 7. Fiabilité

`OpenCodeGoClient.complete()` implémente :

- **timeout** explicite (`LLM_TIMEOUT_SECONDS`, 60 s) ;
- **retries** sur `408, 409, 425, 429, 500, 502, 503, 504` et erreurs réseau ;
- **backoff exponentiel + jitter** : 1 s, 2 s, 4 s… pour éviter les retries
  synchronisés ;
- **`Retry-After`** respecté, plafonné à 30 s ;
- **repli JSON mode** : si le fournisseur répond 400 en mentionnant
  `response_format`, on réessaie une fois sans ce champ ;
- **erreurs typées** : 503 configuration, 502 fournisseur, 504 timeout.

Ce qui n'est **pas** implémenté et qu'il faudrait ajouter pour un usage intensif :

- idempotence : un double clic crée deux lettres. Solution : un `request_id`
  généré côté client + contrainte unique ;
- circuit breaker par modèle ;
- file d'attente : les appels longs (9 s ici) bloquent un worker Flask ;
- budget maximal par jour.

## 8. Coûts et observabilité

Chaque appel écrit une ligne `llm_call` :

```
task, model, prompt_version, status, prompt_tokens, completion_tokens,
cost_usd, duration_ms, error, created_at
```

`GET /api/llm/usage` agrège ces lignes, et la page Réglages les affiche.

L'estimation (`catalog.estimate_cost_usd`) utilise les prix par million de tokens
du catalogue. Elle ignore :

- les lectures de cache ;
- les tarifs heures pleines / heures creuses de DeepSeek ;
- les éventuelles remises.

C'est un **indicateur de pilotage**, pas une facture.

Exemple réel mesuré pendant le développement :

```
claude-haiku-5-5 · 1 526 tokens entrée + 1 887 sortie · 9,0 s · 0,001096 $
```

Le coût est marginal, mais le nombre d'appels et la taille du contexte sont les
deux leviers : un pré-filtre des offres et un CV borné comptent plus que le choix
du modèle.

## 9. Évaluation

Les tests unitaires avec `MockLLMClient` vérifient la plomberie, pas la qualité.
Pour évaluer la qualité :

1. **Constituer un jeu d'offres** : 10 à 20 annonces réelles, variées (tech,
   secteur, taille d'entreprise, niveau), avec le même profil.
2. **Définir une grille** : factualité (aucune invention), respect de la structure,
   spécificité à l'offre, ton, longueur, absence de formules creuses.
3. **Noter à l'aveugle** : mêmes offres, plusieurs modèles/prompts, sans savoir
   lequel a produit quoi.
4. **Mesurer aussi les échecs** : JSON invalide, réponse vide, troncature,
   `finish_reason=length`, latence, coût.
5. **Versionner** : `prompt_version`, modèle, température et date dans chaque
   ligne. Un changement de prompt sans version rend toute comparaison invalide.
6. **Automatiser partiellement** : un juge LLM peut pré-trier, mais il doit être
   validé contre une notation humaine. Il ne remplace pas la relecture.

Taxonomie d'erreurs utile :

- invention d'expérience ou de diplôme ;
- lettre générique, réutilisable pour n'importe quelle offre ;
- structure de la lettre type ignorée ;
- mauvaise entreprise ou mauvais intitulé ;
- ton trop familier ou trop emphatique ;
- dépassement de longueur ;
- sortie non conforme au schéma.

## 10. Sécurité et vie privée

- La clé ne quitte jamais Flask : `/api/health` n'expose que des booléens.
  Aucun log ne contient la clé ni les prompts complets.
- Le CV est une donnée personnelle. Il est stocké localement, mais envoyé au
  fournisseur à chaque génération. Les réglages de confidentialité du workspace
  OpenCode Go (régions, entraînement sur les données) s'appliquent : à vérifier
  dans la Console.
- **Prompt injection** : une annonce malveillante peut tenter de détourner le
  modèle. Les délimiteurs et la règle « les balises sont des données » réduisent
  le risque ; ils ne l'annulent pas. Ne donnez jamais au modèle d'accès à des
  outils ou à des secrets dans cette tâche.
- **Sortie non fiable** : la lettre est stockée et affichée comme du texte. Vue
  échappe le contenu ; on ne l'injecte jamais comme HTML.
- **Coût** : `MAX_SCORING_PER_SCAN` et les bornes de contexte limitent l'exposition.

## 11. Ajouter une nouvelle tâche LLM (exemple : scoring)

1. Écrire le prompt système dans `app/scoring/prompts/score_system.md` et définir
   `PROMPT_VERSION = "score/v1"`.
2. Définir le schéma de sortie :
   ```json
   { "score": 0, "reasons": ["…"], "blockers": ["…"] }
   ```
3. Créer `app/scoring/service.py` sur le modèle de `letters/service.py` :
   construire le contexte, appeler `client.complete(..., json_mode=True)`,
   parser, enregistrer le score et un `llm_call` avec `task="scoring"`.
4. Valider la sortie : score entier 0-100, listes de chaînes, taille bornée.
5. Tester avec `MockLLMClient` (réponse déterministe) puis avec de vraies offres.
6. Évaluer sur un jeu d'offres annotées : précision du tri, faux positifs,
   faux négatifs, coût par offre.

Le scoring est détaillé dans [`scoring.md`](scoring.md).

## 12. Mode démo et tests

Sans clé :

```bash
LLM_PROVIDER=mock .venv/bin/python run.py
```

ou dans `.env` :

```
LLM_PROVIDER=mock
```

`MockLLMClient` renvoie une lettre JSON plausible et un « OK (mode démo) » pour
le test de connexion. Tous les tests backend utilisent ce client, sauf
`tests/test_llm_client.py`, qui teste le vrai client HTTP avec
`httpx.MockTransport` : headers, retries, timeout, repli JSON, coût.

## 13. Exercices

1. Passer la longueur cible de 250-350 à 150-200 mots et comparer sur 5 offres.
2. Ajouter un paramètre `ton` (`sobre`, `enthousiaste`, `technique`) de bout en
   bout : formulaire Vue, validation Flask, prompt.
3. Comparer `claude-haiku-5-5` et `deepseek-v4.1-flash` à l'aveugle sur 10 offres,
   puis calculer coût et temps moyens.
4. Construire le jeu d'évaluation et la grille de notation décrits en section 9.
5. Implémenter le scoring des offres en réutilisant le client et la télémétrie.
6. Ajouter un cache par empreinte de contenu : même CV + même offre = même lettre,
   sans nouvel appel.
7. Ajouter un `request_id` et une contrainte d'unicité pour rendre la génération
   idempotente.
