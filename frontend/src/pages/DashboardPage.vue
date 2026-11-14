<script setup lang="ts">
import { computed, onMounted } from 'vue'
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Database,
  KeyRound,
  Building2,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
} from '@lucide/vue'
import { RouterLink } from 'vue-router'

import StatusPill from '@/components/StatusPill.vue'
import { useHealthStore } from '@/stores/health'

type Tone = 'ok' | 'warn' | 'error' | 'muted'
type StepState = 'done' | 'current' | 'next'

interface RoadmapStep {
  phase: string
  title: string
  detail: string
  state: StepState
}

const health = useHealthStore()

onMounted(() => {
  void health.refresh()
})

const apiTone = computed<Tone>(() => {
  if (health.status === 'ok') return 'ok'
  if (health.status === 'loading' || health.status === 'idle') return 'muted'
  return 'error'
})

const apiLabel = computed(() => {
  if (health.status === 'ok') return 'En ligne'
  if (health.status === 'loading') return 'Connexion'
  if (health.status === 'idle') return 'En attente'
  return 'Hors ligne'
})

const apiValue = computed(() => (health.data ? `v${health.data.version}` : '—'))

const llmReady = computed(() => health.data?.llm.ready ?? false)
const llmMock = computed(() => health.data?.llm.mock ?? false)
const llmLabel = computed(() =>
  llmMock.value ? 'Mode démo' : llmReady.value ? 'Prêt' : 'À configurer',
)

const lastChecked = computed(() => {
  if (!health.lastCheckedAt) return 'jamais'
  return health.lastCheckedAt.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
})

const roadmap: RoadmapStep[] = [
  {
    phase: '1',
    title: 'Socle Flask + Vue',
    detail: 'API JSON, CORS, route de santé, tableau de bord, tests.',
    state: 'done',
  },
  {
    phase: '2',
    title: 'Profil & campagne',
    detail: 'CV PDF, lettre type, critères de recherche, durée.',
    state: 'done',
  },
  {
    phase: '3',
    title: 'LLM & lettres',
    detail: 'Client OpenCode Go, sélection des modèles, génération.',
    state: 'done',
  },
  {
    phase: '4',
    title: 'Employeurs & ATS',
    detail: 'Watchlist, détection ATS, collecte directe des offres.',
    state: 'done',
  },
  {
    phase: '5',
    title: 'Scrapers & APIs',
    detail: 'WTTJ sitemap, Adzuna et Jooble en complément.',
    state: 'current',
  },
  {
    phase: '6',
    title: 'Scoring & scheduler',
    detail: 'Déduplication, pré-filtre, scoring LLM, scans planifiés.',
    state: 'next',
  },
  {
    phase: '7',
    title: 'Interface offres',
    detail: 'Cartes triées, filtres, trois boutons, statuts.',
    state: 'next',
  },
]

const stepDot: Record<StepState, string> = {
  done: 'bg-emerald-500',
  current: 'bg-neutral-900 ring-4 ring-neutral-200',
  next: 'bg-neutral-300',
}
</script>

<template>
  <div class="space-y-6">
    <!-- Hero -->
    <section class="card relative overflow-hidden px-6 py-7 md:px-8">
      <div
        class="pointer-events-none absolute -right-20 -top-28 h-64 w-64 rounded-full bg-emerald-100/70 blur-3xl"
      />
      <div class="relative flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div class="max-w-2xl">
          <StatusPill
            :tone="apiTone"
            :label="apiLabel"
            :pulse="health.status === 'loading'"
          />
          <h2 class="mt-4 text-2xl font-semibold tracking-tight">La collecte employeurs est branchée.</h2>
          <p class="mt-2 text-sm leading-6 text-neutral-600">
            200 employeurs IA en watchlist, 17 ATS vérifiés, et les offres sont récupérées avec
            leur lien de candidature d’origine. Les prochaines étapes ajoutent le scoring et les
            job boards en complément.
          </p>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <RouterLink to="/employeurs" class="btn-primary">
            Gérer les employeurs
            <ArrowRight :size="16" />
          </RouterLink>
          <button
            type="button"
            class="btn-ghost"
            :disabled="health.status === 'loading'"
            title="Revérifier la connexion"
            @click="health.refresh()"
          >
            <RefreshCw :size="16" :class="health.status === 'loading' ? 'animate-spin' : ''" />
            <span class="sr-only">Revérifier</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Status grid -->
    <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <article class="card p-5">
        <div class="flex items-start justify-between">
          <div class="grid h-9 w-9 place-items-center rounded-xl bg-neutral-100 text-neutral-600">
            <Server :size="18" :stroke-width="1.9" />
          </div>
          <StatusPill :tone="apiTone" :label="apiLabel" />
        </div>
        <p class="label mt-4">API Flask</p>
        <p class="mt-1 text-lg font-semibold tracking-tight">{{ apiValue }}</p>
        <p class="mt-1 line-clamp-2 text-xs leading-5 text-neutral-500">
          <template v-if="health.data">
            {{ health.data.environment }} · {{ health.data.service }}
          </template>
          <template v-else-if="health.error">{{ health.error }}</template>
          <template v-else>Interrogation de /api/health…</template>
        </p>
      </article>

      <article class="card p-5">
        <div class="flex items-start justify-between">
          <div class="grid h-9 w-9 place-items-center rounded-xl bg-neutral-100 text-neutral-600">
            <Sparkles :size="18" :stroke-width="1.9" />
          </div>
          <StatusPill
            :tone="llmMock ? 'warn' : llmReady ? 'ok' : 'warn'"
            :label="llmLabel"
          />
        </div>
        <p class="label mt-4">OpenCode Go</p>
        <p class="mt-1 truncate font-mono text-sm font-medium">
          {{ health.data?.llm.letter_model ?? '—' }}
        </p>
        <p class="mt-1 text-xs leading-5 text-neutral-500">
          {{ health.data?.llm.provider ?? '—' }} ·
          {{ llmMock ? 'réponses simulées' : llmReady ? 'clé détectée' : 'clé absente' }}
        </p>
      </article>

      <article class="card p-5">
        <div class="flex items-start justify-between">
          <div class="grid h-9 w-9 place-items-center rounded-xl bg-neutral-100 text-neutral-600">
            <Database :size="18" :stroke-width="1.9" />
          </div>
          <StatusPill
            :tone="health.data?.features.database ? 'ok' : 'muted'"
            :label="health.data?.features.database ? 'Opérationnelle' : 'Phase 2'"
          />
        </div>
        <p class="label mt-4">Base de données</p>
        <p class="mt-1 text-lg font-semibold tracking-tight">SQLite</p>
        <p class="mt-1 text-xs leading-5 text-neutral-500">
          Profil et campagne persistés dans <code class="font-mono">backend/instance</code>.
        </p>
      </article>

      <article class="card p-5">
        <div class="flex items-start justify-between">
          <div class="grid h-9 w-9 place-items-center rounded-xl bg-neutral-100 text-neutral-600">
            <Building2 :size="18" :stroke-width="1.9" />
          </div>
          <StatusPill
            :tone="health.data?.features.employers ? 'ok' : 'muted'"
            :label="health.data?.features.employers ? 'Opérationnelle' : 'Phase 4'"
          />
        </div>
        <p class="label mt-4">Employeurs</p>
        <p class="mt-1 text-lg font-semibold tracking-tight">200 en watchlist</p>
        <p class="mt-1 text-xs leading-5 text-neutral-500">
          IA France · 17 ATS vérifiés · collecte directe et lien employeur.
        </p>
      </article>
    </section>

    <!-- Roadmap + configuration -->
    <section class="grid gap-6 lg:grid-cols-5">
      <article class="card p-6 lg:col-span-3">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-semibold tracking-tight">Feuille de route</h3>
            <p class="mt-0.5 text-xs text-neutral-500">Sept étapes, chacune utilisable en l’état.</p>
          </div>
          <span class="rounded-full bg-neutral-100 px-2.5 py-1 text-[11px] font-medium text-neutral-500">
            4 / 7
          </span>
        </div>

        <ol class="mt-4 divide-y divide-neutral-100">
          <li v-for="step in roadmap" :key="step.phase" class="flex gap-3 py-3">
            <div class="flex w-3 justify-center">
              <span class="mt-1.5 h-2 w-2 rounded-full" :class="stepDot[step.state]" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p
                  class="text-sm font-medium"
                  :class="step.state === 'next' ? 'text-neutral-500' : 'text-neutral-900'"
                >
                  {{ step.title }}
                </p>
                <span
                  v-if="step.state === 'current'"
                  class="rounded-full bg-neutral-900 px-2 py-0.5 text-[10px] font-semibold text-white"
                >
                  En cours
                </span>
                <Check v-else-if="step.state === 'done'" :size="14" class="text-emerald-600" />
              </div>
              <p class="mt-0.5 text-xs leading-5 text-neutral-500">{{ step.detail }}</p>
            </div>
            <span class="pt-0.5 text-[11px] font-medium text-neutral-400">P{{ step.phase }}</span>
          </li>
        </ol>
      </article>

      <article class="card flex flex-col p-6 lg:col-span-2">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="flex items-center gap-2 text-sm font-semibold tracking-tight">
              <KeyRound :size="16" class="text-neutral-500" />
              Configuration LLM
            </h3>
            <p class="mt-0.5 text-xs text-neutral-500">OpenCode Go, via une API compatible OpenAI.</p>
          </div>
          <RouterLink
            to="/reglages"
            class="text-xs font-medium text-emerald-700 transition-colors hover:text-emerald-800"
          >
            Réglages
          </RouterLink>
        </div>

        <dl class="mt-5 space-y-3 text-sm">
          <div class="flex items-baseline justify-between gap-4">
            <dt class="text-neutral-500">Modèle de scoring</dt>
            <dd class="truncate font-mono text-xs font-medium">
              {{ health.data?.llm.scoring_model ?? '—' }}
            </dd>
          </div>
          <div class="flex items-baseline justify-between gap-4">
            <dt class="text-neutral-500">Modèle de lettre</dt>
            <dd class="truncate font-mono text-xs font-medium">
              {{ health.data?.llm.letter_model ?? '—' }}
            </dd>
          </div>
          <div class="flex items-baseline justify-between gap-4">
            <dt class="text-neutral-500">URL de base</dt>
            <dd class="font-medium">
              <StatusPill
                :tone="health.data?.llm.base_url_configured ? 'ok' : 'warn'"
                :label="health.data?.llm.base_url_configured ? 'Renseignée' : 'Manquante'"
              />
            </dd>
          </div>
          <div class="flex items-baseline justify-between gap-4">
            <dt class="text-neutral-500">Clé API</dt>
            <dd class="font-medium">
              <StatusPill
                :tone="llmMock ? 'muted' : llmReady ? 'ok' : 'warn'"
                :label="llmMock ? 'Non requise (démo)' : llmReady ? 'Détectée côté serveur' : 'Absente'"
              />
            </dd>
          </div>
        </dl>

        <div
          v-if="llmReady"
          class="mt-5 flex gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs leading-5 text-emerald-800"
        >
          <ShieldCheck :size="16" class="mt-0.5 shrink-0" />
          <p v-if="llmMock">
            Mode démo actif : les réponses sont simulées localement, aucun appel réseau.
          </p>
          <p v-else>
            La clé reste dans <code class="font-mono">backend/.env</code>. Le navigateur ne reçoit
            qu’un booléen de configuration.
          </p>
        </div>

        <div
          v-else
          class="mt-5 flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs leading-5 text-amber-800"
        >
          <AlertTriangle :size="16" class="mt-0.5 shrink-0" />
          <p>
            Renseigne <code class="font-mono">OPENCODE_BASE_URL</code> et
            <code class="font-mono">OPENCODE_API_KEY</code> dans <code class="font-mono">.env</code>,
            puis redémarre Flask. La génération sera branchée en phase 3.
          </p>
        </div>

        <div class="mt-auto flex items-center justify-between border-t border-neutral-100 pt-4">
          <p class="text-[11px] text-neutral-400">Dernière vérification : {{ lastChecked }}</p>
          <button
            type="button"
            class="text-[11px] font-medium text-neutral-600 transition-colors hover:text-neutral-900 disabled:opacity-50"
            :disabled="health.status === 'loading'"
            @click="health.refresh()"
          >
            Actualiser
          </button>
        </div>
      </article>
    </section>
  </div>
</template>
