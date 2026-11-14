<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  AlertCircle,
  Building2,
  Check,
  Download,
  LoaderCircle,
  Plus,
  Radar,
  RefreshCw,
  Search,
} from '@lucide/vue'

import { ApiError } from '@/api/client'
import type { EmployerSource } from '@/api/types'
import StatusPill from '@/components/StatusPill.vue'
import { messageOf, useEmployersStore } from '@/stores/employers'

type Tone = 'ok' | 'warn' | 'error' | 'muted'
type StatusFilter = 'all' | 'ready' | 'pending' | 'no_ats' | 'error'

const store = useEmployersStore()

const STATUS_META: Record<EmployerSource['status'], { label: string; tone: Tone }> = {
  ready: { label: 'Prêt', tone: 'ok' },
  pending: { label: 'À découvrir', tone: 'muted' },
  no_ats: { label: 'Sans ATS', tone: 'warn' },
  error: { label: 'Erreur', tone: 'error' },
}

const search = ref('')
const statusFilter = ref<StatusFilter>('all')
const feedback = ref<{ tone: 'ok' | 'error'; text: string } | null>(null)
const fieldErrors = ref<Record<string, string>>({})

const form = reactive({
  domain: '',
  name: '',
  careers_url: '',
})

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  const matches = store.employers.filter((employer) => {
    if (statusFilter.value !== 'all' && employer.status !== statusFilter.value) {
      return false
    }
    if (!query) {
      return true
    }
    return (
      employer.name.toLowerCase().includes(query) ||
      employer.domain.toLowerCase().includes(query) ||
      employer.ats_slug.toLowerCase().includes(query)
    )
  })

  const order: Record<EmployerSource['status'], number> = {
    ready: 0,
    pending: 1,
    no_ats: 2,
    error: 3,
  }
  return matches.sort(
    (a, b) => order[a.status] - order[b.status] || a.name.localeCompare(b.name),
  )
})

onMounted(async () => {
  try {
    await store.load()
  } catch {
    // Store error is displayed above.
  }
})

function notify(tone: 'ok' | 'error', text: string): void {
  feedback.value = { tone, text }
  window.setTimeout(() => {
    if (feedback.value?.text === text) {
      feedback.value = null
    }
  }, 6000)
}

async function seedWatchlist(): Promise<void> {
  try {
    const payload = await store.seed()
    notify(
      'ok',
      `Watchlist chargée : ${payload.seed.created} ajoutés, ${payload.seed.updated} mis à jour.`,
    )
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function discoverBatch(): Promise<void> {
  try {
    const summary = await store.discover(8)
    notify(
      'ok',
      `${summary.checked} employeurs analysés : ${summary.ready} ATS trouvés, ${summary.no_ats} sans ATS.`,
    )
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function collectBatch(): Promise<void> {
  try {
    const summary = await store.collect(5, 50)
    notify(
      'ok',
      `${summary.found} offres vues, ${summary.new} nouvelles, ${summary.updated} doublons mis à jour.`,
    )
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function addEmployer(): Promise<void> {
  fieldErrors.value = {}
  try {
    const employer = await store.add({
      domain: form.domain,
      name: form.name || undefined,
      careers_url: form.careers_url || undefined,
    })
    form.domain = ''
    form.name = ''
    form.careers_url = ''
    if (employer.status === 'ready') {
      notify('ok', `${employer.name} ajouté, ATS ${employer.ats_type} détecté.`)
    } else {
      notify(
        'ok',
        `${employer.name} ajouté. ATS non détecté pour l’instant : relance la détection plus tard.`,
      )
    }
  } catch (cause) {
    if (cause instanceof ApiError) {
      fieldErrors.value = cause.fields
    }
    notify('error', messageOf(cause))
  }
}

async function toggleEmployer(employer: EmployerSource): Promise<void> {
  try {
    await store.toggle(employer.id, !employer.enabled)
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function collectEmployer(employer: EmployerSource): Promise<void> {
  try {
    const result = await store.collectOne(employer.id)
    if (result.error) {
      notify('error', `${employer.name} : ${result.error}`)
    } else {
      notify('ok', `${employer.name} : ${result.found} offres, ${result.new} nouvelles.`)
    }
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleString('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="space-y-6">
    <Transition name="fade">
      <div
        v-if="feedback"
        class="flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm"
        :class="
          feedback.tone === 'ok'
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
            : 'border-rose-200 bg-rose-50 text-rose-800'
        "
      >
        <Check v-if="feedback.tone === 'ok'" :size="16" class="mt-0.5 shrink-0" />
        <AlertCircle v-else :size="16" class="mt-0.5 shrink-0" />
        <p>{{ feedback.text }}</p>
      </div>
    </Transition>

    <!-- Overview -->
    <section class="card p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="max-w-2xl">
          <h2 class="flex items-center gap-2 text-sm font-semibold tracking-tight">
            <Building2 :size="16" class="text-neutral-500" />
            Watchlist employeurs
          </h2>
          <p class="mt-1.5 text-xs leading-5 text-neutral-500">
            Les offres sont récupérées directement sur les ATS publics des entreprises. Le secteur
            et la zone de test sont l’IA en France ; les critères de ta campagne filtrent ensuite
            les offres affichées.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="(store.stats?.total ?? 0) === 0"
            type="button"
            class="btn-primary"
            :disabled="store.busy !== null"
            @click="seedWatchlist"
          >
            <LoaderCircle v-if="store.busy === 'seed'" :size="15" class="animate-spin" />
            <Download v-else :size="15" />
            Charger la watchlist IA France (200)
          </button>

          <button
            type="button"
            class="btn-ghost"
            :disabled="store.busy !== null || (store.stats?.pending ?? 0) === 0"
            @click="discoverBatch"
          >
            <LoaderCircle v-if="store.busy === 'discover'" :size="15" class="animate-spin" />
            <Radar v-else :size="15" />
            Détecter 8 ATS
          </button>

          <button
            type="button"
            class="btn-ghost"
            :disabled="store.busy !== null || (store.stats?.ready ?? 0) === 0"
            @click="collectBatch"
          >
            <LoaderCircle v-if="store.busy === 'collect'" :size="15" class="animate-spin" />
            <RefreshCw v-else :size="15" />
            Collecter 5 employeurs
          </button>

          <button
            v-if="(store.stats?.total ?? 0) > 0"
            type="button"
            class="btn-ghost"
            :disabled="store.busy !== null"
            @click="seedWatchlist"
          >
            <Download :size="15" />
            Recharger le seed
          </button>
        </div>
      </div>

      <div class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">Employeurs</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">{{ store.stats?.total ?? 0 }}</p>
          <p class="mt-0.5 text-[11px] text-neutral-500">
            {{ store.stats?.enabled ?? 0 }} actifs
          </p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">ATS prêts</p>
          <p class="mt-1 text-xl font-semibold tabular-nums text-emerald-700">
            {{ store.stats?.ready ?? 0 }}
          </p>
          <p class="mt-0.5 text-[11px] text-neutral-500">collecte directe possible</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">À découvrir</p>
          <p class="mt-1 text-xl font-semibold tabular-nums text-amber-700">
            {{ store.stats?.pending ?? 0 }}
          </p>
          <p class="mt-0.5 text-[11px] text-neutral-500">détection par lots de 8</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">Offres stockées</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">{{ store.stats?.offers ?? 0 }}</p>
          <p class="mt-0.5 text-[11px] text-neutral-500">toutes sources employeurs</p>
        </div>
      </div>

      <div
        v-if="(store.stats?.total ?? 0) > 0 && (store.stats?.pending ?? 0) > 0"
        class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800"
      >
        17 ATS sont vérifiés au départ. Les autres employeurs passent par la détection : soit un
        lien ATS trouvé sur leur page carrière, soit des slugs testés sur les API. Clique sur
        « Détecter 8 ATS » plusieurs fois pour avancer.
      </div>
    </section>

    <!-- Add employer -->
    <section class="card p-6">
      <h2 class="text-sm font-semibold tracking-tight">Ajouter un employeur</h2>
      <p class="mt-1 text-xs text-neutral-500">
        Le domaine suffit. Si tu connais l’URL carrières, colle-la pour une détection immédiate.
      </p>

      <form class="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr_1.2fr_auto]" @submit.prevent="addEmployer">
        <div>
          <label class="field-label" for="employer_domain">Domaine</label>
          <input
            id="employer_domain"
            v-model="form.domain"
            class="input"
            type="text"
            placeholder="mistral.ai"
            required
          />
          <p v-if="fieldErrors.domain" class="field-error">{{ fieldErrors.domain }}</p>
        </div>
        <div>
          <label class="field-label" for="employer_name">Nom <span class="font-normal text-neutral-400">(optionnel)</span></label>
          <input id="employer_name" v-model="form.name" class="input" type="text" placeholder="Mistral AI" />
        </div>
        <div>
          <label class="field-label" for="employer_careers">URL carrières <span class="font-normal text-neutral-400">(optionnel)</span></label>
          <input
            id="employer_careers"
            v-model="form.careers_url"
            class="input"
            type="url"
            placeholder="https://jobs.ashbyhq.com/mistral.ai"
          />
          <p v-if="fieldErrors.careers_url" class="field-error">{{ fieldErrors.careers_url }}</p>
        </div>
        <div class="flex items-end">
          <button type="submit" class="btn-primary w-full" :disabled="store.busy !== null || !form.domain">
            <LoaderCircle v-if="store.busy === 'add'" :size="15" class="animate-spin" />
            <Plus v-else :size="15" />
            Ajouter
          </button>
        </div>
      </form>
    </section>

    <!-- Watchlist -->
    <section class="card overflow-hidden">
      <header class="flex flex-col gap-3 border-b border-neutral-100 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold tracking-tight">Employeurs suivis</h2>
          <p class="mt-0.5 text-xs text-neutral-500">
            {{ filtered.length }} affiché(s) sur {{ store.employers.length }}
          </p>
        </div>
        <div class="flex flex-col gap-2 sm:flex-row">
          <div class="relative">
            <Search :size="14" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              v-model="search"
              class="input py-2 pl-9 text-xs"
              type="search"
              placeholder="Nom, domaine, slug ATS…"
            />
          </div>
          <select v-model="statusFilter" class="select py-2 text-xs">
            <option value="all">Tous les statuts</option>
            <option value="ready">Prêts</option>
            <option value="pending">À découvrir</option>
            <option value="no_ats">Sans ATS</option>
            <option value="error">Erreurs</option>
          </select>
          <button
            type="button"
            class="btn-ghost px-3 py-2"
            title="Actualiser"
            :disabled="store.loading"
            @click="store.load()"
          >
            <RefreshCw :size="14" :class="store.loading ? 'animate-spin' : ''" />
          </button>
        </div>
      </header>

      <div class="max-h-[65vh] overflow-auto">
        <table class="w-full min-w-[900px] text-left text-xs">
          <thead class="sticky top-0 z-10 bg-neutral-50 text-neutral-500">
            <tr>
              <th class="px-4 py-2.5 font-medium">Employeur</th>
              <th class="px-4 py-2.5 font-medium">ATS</th>
              <th class="px-4 py-2.5 font-medium">Statut</th>
              <th class="px-4 py-2.5 text-right font-medium">Offres</th>
              <th class="px-4 py-2.5 font-medium">Dernière vérif.</th>
              <th class="px-4 py-2.5 text-center font-medium">Actif</th>
              <th class="px-4 py-2.5 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="employer in filtered" :key="employer.id" class="text-neutral-700">
              <td class="px-4 py-2.5">
                <p class="font-medium text-neutral-900">{{ employer.name }}</p>
                <p class="mt-0.5 text-[11px] text-neutral-400">{{ employer.domain }}</p>
              </td>
              <td class="px-4 py-2.5">
                <span v-if="employer.ats_type" class="rounded-md bg-neutral-100 px-1.5 py-0.5 font-mono text-[10px]">
                  {{ employer.ats_type }} · {{ employer.ats_slug }}
                </span>
                <span v-else class="text-neutral-400">—</span>
              </td>
              <td class="px-4 py-2.5">
                <span :title="employer.last_error">
                  <StatusPill
                    :tone="STATUS_META[employer.status].tone"
                    :label="STATUS_META[employer.status].label"
                  />
                </span>
              </td>
              <td class="px-4 py-2.5 text-right tabular-nums">{{ employer.offer_count }}</td>
              <td class="px-4 py-2.5 text-neutral-500">{{ formatDate(employer.last_checked_at) }}</td>
              <td class="px-4 py-2.5 text-center">
                <input
                  type="checkbox"
                  class="h-4 w-4 accent-emerald-600"
                  :checked="employer.enabled"
                  :aria-label="`Activer ${employer.name}`"
                  @change="toggleEmployer(employer)"
                />
              </td>
              <td class="px-4 py-2.5 text-right">
                <button
                  v-if="employer.status === 'ready'"
                  type="button"
                  class="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900 disabled:opacity-40"
                  :disabled="store.busy !== null"
                  title="Collecter les offres de cet employeur"
                  @click="collectEmployer(employer)"
                >
                  <RefreshCw :size="12" />
                  Collecter
                </button>
                <span v-else class="text-[11px] text-neutral-300">—</span>
              </td>
            </tr>
            <tr v-if="filtered.length === 0">
              <td colspan="7" class="px-4 py-12 text-center text-neutral-500">
                {{
                  store.employers.length === 0
                    ? 'Watchlist vide. Charge le seed IA France pour commencer.'
                    : 'Aucun employeur ne correspond à ce filtre.'
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
