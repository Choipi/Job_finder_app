<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileText,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Undo2,
  X,
} from '@lucide/vue'
import { RouterLink, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import type { ManualOfferPayload, OfferDetail, OfferStatus, OfferSummary } from '@/api/types'
import { messageOf, useOffersStore } from '@/stores/offers'

const store = useOffersStore()
const router = useRouter()

const search = ref('')
const remote = ref('')
const status = ref('')
const minScore = ref(0)
const sort = ref<'score' | 'date'>('score')
const filterByCampaign = ref(true)
const feedback = ref<{ tone: 'ok' | 'error'; text: string } | null>(null)
const undo = ref<{ id: number; title: string } | null>(null)
const expanded = ref<number | null>(null)
const details = ref<Record<number, OfferDetail>>({})
const detailsLoading = ref<number | null>(null)
const showManual = ref(false)
const manualErrors = ref<Record<string, string>>({})
const manual = reactive<ManualOfferPayload>({
  title: '',
  company: '',
  location: '',
  source_url: '',
  contract_type: '',
  remote: '',
  description: '',
})
let undoTimer: number | undefined

const REMOTE_LABELS: Record<string, string> = {
  remote: 'Télétravail',
  hybrid: 'Hybride',
  onsite: 'Sur site',
}

const STATUS_OPTIONS: Array<{ value: OfferStatus; label: string }> = [
  { value: 'new', label: 'Nouvelle' },
  { value: 'to_apply', label: 'À postuler' },
  { value: 'applied', label: 'Postulée' },
  { value: 'interview', label: 'Entretien' },
  { value: 'rejected', label: 'Refusée' },
]

onMounted(async () => {
  try {
    await load()
  } catch {
    // Store error is displayed above.
  }
})

async function load(): Promise<void> {
  await store.load({
    q: search.value,
    remote: remote.value,
    status: status.value,
    minScore: minScore.value,
    sort: sort.value,
    limit: 200,
    campaign: filterByCampaign.value,
  })
}

function notify(tone: 'ok' | 'error', text: string): void {
  feedback.value = { tone, text }
  window.setTimeout(() => {
    if (feedback.value?.text === text) {
      feedback.value = null
    }
  }, 6000)
}

function resetManual(): void {
  manual.title = ''
  manual.company = ''
  manual.location = ''
  manual.source_url = ''
  manual.contract_type = ''
  manual.remote = ''
  manual.description = ''
  manualErrors.value = {}
}

function toggleManual(): void {
  showManual.value = !showManual.value
  if (!showManual.value) {
    resetManual()
  }
}

async function createManual(andWrite: boolean): Promise<void> {
  manualErrors.value = {}
  try {
    const result = await store.createManual({ ...manual })
    const createdTitle = result.offer.title
    showManual.value = false
    resetManual()
    filterByCampaign.value = false
    search.value = createdTitle
    await load()

    if (andWrite) {
      await router.push({ path: '/lettres', query: { offer: result.offer.id } })
      return
    }
    notify(
      'ok',
      result.created
        ? 'Offre ajoutée. Tu peux la scorer ou générer une lettre.'
        : 'Une offre identique existait déjà ; elle a été réaffichée.',
    )
  } catch (cause) {
    if (cause instanceof ApiError) {
      manualErrors.value = cause.fields
    }
    notify('error', messageOf(cause))
  }
}

function sourceLabel(source: string): string {
  if (source === 'manual') return 'Ajout manuel'
  if (source === 'employer_ats') return 'ATS employeur'
  return source
}

async function scoreBatch(): Promise<void> {
  try {
    const summary = await store.score(20)
    if (summary.skipped === 'profile_empty') {
      notify('error', 'Complète ton profil (CV ou présentation) avant de scorer les offres.')
      return
    }
    notify(
      'ok',
      `${summary.scored} offre(s) scorée(s), ${summary.filtered} filtrée(s), ${summary.errors} erreur(s).`,
    )
    await load()
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function changeStatus(offer: OfferSummary, value: string): Promise<void> {
  try {
    await store.updateStatus(offer.id, value as OfferStatus)
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

function onStatusChange(offer: OfferSummary, event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  void changeStatus(offer, value)
}

function markApplied(offer: OfferSummary): void {
  if (!offer.apply_url) {
    return
  }
  window.open(offer.apply_url, '_blank', 'noopener,noreferrer')
  void store.updateStatus(offer.id, 'applied').catch((cause) => {
    notify('error', messageOf(cause))
  })
}

async function deleteOffer(offer: OfferSummary): Promise<void> {
  try {
    await store.remove(offer.id)
    if (expanded.value === offer.id) {
      expanded.value = null
    }
    undo.value = { id: offer.id, title: offer.title }
    window.clearTimeout(undoTimer)
    undoTimer = window.setTimeout(() => {
      undo.value = null
    }, 8000)
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function restoreOffer(): Promise<void> {
  if (!undo.value) {
    return
  }
  try {
    await store.restore(undo.value.id)
    undo.value = null
    await load()
    notify('ok', 'Offre restaurée.')
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function toggleDetails(offer: OfferSummary): Promise<void> {
  if (expanded.value === offer.id) {
    expanded.value = null
    return
  }
  expanded.value = offer.id
  if (!details.value[offer.id]) {
    detailsLoading.value = offer.id
    try {
      details.value[offer.id] = await store.getDetail(offer.id)
    } catch (cause) {
      notify('error', messageOf(cause))
    } finally {
      detailsLoading.value = null
    }
  }
}

function scoreClass(score: number | null, status: string | null): string {
  if (status === 'filtered') return 'bg-neutral-100 text-neutral-500'
  if (score === null) return 'bg-neutral-100 text-neutral-500'
  if (score >= 75) return 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20'
  if (score >= 50) return 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20'
  return 'bg-neutral-100 text-neutral-600'
}

function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
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

    <Transition name="fade">
      <div
        v-if="store.error"
        class="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
      >
        <AlertCircle :size="16" class="mt-0.5 shrink-0" />
        <p class="flex-1">{{ store.error }}</p>
        <RouterLink to="/reglages" class="text-xs font-medium underline">Réglages</RouterLink>
      </div>
    </Transition>

    <!-- Controls -->
    <section class="card p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold tracking-tight">Offres collectées</h2>
          <p class="mt-1 text-xs leading-5 text-neutral-500">
            {{ store.stats?.total ?? store.total }} offres · {{ store.stats?.scored ?? 0 }} scorées ·
            {{ store.stats?.applied ?? 0 }} postulées
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" class="btn-ghost" @click="toggleManual">
            <X v-if="showManual" :size="15" />
            <Plus v-else :size="15" />
            {{ showManual ? 'Fermer' : 'Ajouter une offre' }}
          </button>
          <button type="button" class="btn-ghost" :disabled="store.loading" @click="load">
            <LoaderCircle v-if="store.loading" :size="15" class="animate-spin" />
            <RefreshCw v-else :size="15" />
            Actualiser
          </button>
          <button type="button" class="btn-primary" :disabled="store.scoring" @click="scoreBatch">
            <LoaderCircle v-if="store.scoring" :size="15" class="animate-spin" />
            <Sparkles v-else :size="15" />
            {{ store.scoring ? 'Scoring en cours…' : 'Scorer 20 offres' }}
          </button>
        </div>
      </div>

      <form class="mt-5 grid gap-2 border-t border-neutral-100 pt-5 sm:grid-cols-2 lg:grid-cols-6" @submit.prevent="load">
        <div class="relative lg:col-span-2">
          <Search :size="14" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input v-model="search" class="input py-2 pl-9 text-xs" type="search" placeholder="Titre de l’offre…" />
        </div>
        <select v-model="remote" class="select py-2 text-xs">
          <option value="">Tous les modes</option>
          <option value="remote">Télétravail</option>
          <option value="hybrid">Hybride</option>
          <option value="onsite">Sur site</option>
        </select>
        <select v-model="status" class="select py-2 text-xs">
          <option value="">Tous les statuts</option>
          <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <select v-model.number="minScore" class="select py-2 text-xs">
          <option :value="0">Tous les scores</option>
          <option :value="50">Score ≥ 50</option>
          <option :value="60">Score ≥ 60</option>
          <option :value="70">Score ≥ 70</option>
          <option :value="80">Score ≥ 80</option>
          <option :value="90">Score ≥ 90</option>
        </select>
        <select v-model="sort" class="select py-2 text-xs">
          <option value="score">Tri : score</option>
          <option value="date">Tri : date</option>
        </select>
        <button type="submit" class="btn-ghost px-3 py-2 text-xs lg:col-span-6 lg:justify-self-start">
          Appliquer les filtres
        </button>
      </form>

      <div class="mt-3 flex flex-col gap-2 border-t border-neutral-100 pt-3 sm:flex-row sm:items-center sm:justify-between">
        <label class="inline-flex cursor-pointer items-center gap-2 text-xs text-neutral-600">
          <input v-model="filterByCampaign" type="checkbox" class="h-4 w-4 accent-emerald-600" @change="load" />
          Filtrer selon ma campagne (mots-clés, lieux, télétravail)
        </label>
        <p v-if="store.campaignFilter?.active" class="text-[11px] text-neutral-400">
          <template v-if="store.campaignFilter.keywords.length > 0">
            Mots-clés : {{ store.campaignFilter.keywords.join(', ') }}
          </template>
          <template v-else>Aucun mot-clé dans la campagne.</template>
          <template v-if="store.campaignFilter.locations.length > 0">
            · Lieux : {{ store.campaignFilter.locations.join(', ') }}
          </template>
        </p>
      </div>
    </section>

    <!-- Manual offer -->
    <section v-if="showManual" class="card p-6">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold tracking-tight">Ajouter une offre manuellement</h2>
          <p class="mt-1 max-w-2xl text-xs leading-5 text-neutral-500">
            Colle une annonce trouvée ailleurs. Elle sera ajoutée à la liste, pourra être scorée
            et servira de base à une lettre de motivation.
          </p>
        </div>
        <button
          type="button"
          class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
          aria-label="Fermer"
          @click="toggleManual"
        >
          <X :size="16" />
        </button>
      </div>

      <form class="mt-5 space-y-4" @submit.prevent="createManual(false)">
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="field-label" for="manual_title">Intitulé du poste</label>
            <input
              id="manual_title"
              v-model="manual.title"
              class="input"
              type="text"
              maxlength="300"
              placeholder="Développeur Python Senior"
              required
            />
            <p v-if="manualErrors.title" class="field-error">{{ manualErrors.title }}</p>
          </div>
          <div>
            <label class="field-label" for="manual_company">Entreprise</label>
            <input
              id="manual_company"
              v-model="manual.company"
              class="input"
              type="text"
              maxlength="200"
              placeholder="DataForge"
              required
            />
            <p v-if="manualErrors.company" class="field-error">{{ manualErrors.company }}</p>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="field-label" for="manual_location">Lieu <span class="font-normal text-neutral-400">(optionnel)</span></label>
            <input
              id="manual_location"
              v-model="manual.location"
              class="input"
              type="text"
              maxlength="200"
              placeholder="Paris, Remote…"
            />
          </div>
          <div>
            <label class="field-label" for="manual_url">Lien de l’annonce <span class="font-normal text-neutral-400">(optionnel)</span></label>
            <input
              id="manual_url"
              v-model="manual.source_url"
              class="input"
              type="url"
              maxlength="700"
              placeholder="https://…"
            />
            <p v-if="manualErrors.source_url" class="field-error">{{ manualErrors.source_url }}</p>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="field-label" for="manual_remote">Télétravail</label>
            <select id="manual_remote" v-model="manual.remote" class="select">
              <option value="">Non précisé</option>
              <option value="remote">Télétravail complet</option>
              <option value="hybrid">Hybride</option>
              <option value="onsite">Sur site</option>
            </select>
          </div>
          <div>
            <label class="field-label" for="manual_contract">Contrat <span class="font-normal text-neutral-400">(optionnel)</span></label>
            <input
              id="manual_contract"
              v-model="manual.contract_type"
              class="input"
              type="text"
              maxlength="80"
              placeholder="CDI, CDD, Freelance…"
            />
          </div>
        </div>

        <div>
          <label class="field-label" for="manual_description">Texte de l’offre</label>
          <textarea
            id="manual_description"
            v-model="manual.description"
            class="textarea"
            rows="9"
            maxlength="30000"
            placeholder="Colle ici l’annonce complète : missions, technologies, équipe, localisation…"
            required
          />
          <div class="mt-1.5 flex items-start justify-between gap-4">
            <p class="field-hint">
              Le scoring et la lettre utilisent ce texte. 40 caractères minimum.
            </p>
            <p class="shrink-0 text-[11px] tabular-nums text-neutral-400">
              {{ manual.description.length.toLocaleString('fr-FR') }} / 30 000
            </p>
          </div>
          <p v-if="manualErrors.description" class="field-error">{{ manualErrors.description }}</p>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-4">
          <p class="text-xs text-neutral-500">
            L’ajout manuel désactive le filtre campagne pour rendre l’offre visible.
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <button type="button" class="btn-ghost" :disabled="store.creating" @click="createManual(true)">
              <FileText :size="15" />
              Ajouter et rédiger la lettre
            </button>
            <button type="submit" class="btn-primary" :disabled="store.creating">
              <LoaderCircle v-if="store.creating" :size="15" class="animate-spin" />
              <Plus v-else :size="15" />
              Ajouter l’offre
            </button>
          </div>
        </div>
      </form>
    </section>

    <!-- Offer cards -->
    <div v-if="store.offers.length > 0" class="grid gap-4 xl:grid-cols-2">
      <article v-for="offer in store.offers" :key="offer.id" class="card flex flex-col p-5">
        <div class="flex items-start gap-4">
          <div
            class="grid h-12 w-12 shrink-0 place-items-center rounded-xl text-sm font-semibold tabular-nums"
            :class="scoreClass(offer.score, offer.score_status)"
            :title="offer.score_status === 'filtered' ? 'Filtrée par les critères' : 'Score de pertinence'"
          >
            <span v-if="offer.score !== null">{{ offer.score }}</span>
            <span v-else class="text-[10px] font-medium">—</span>
          </div>

          <div class="min-w-0 flex-1">
            <h3 class="text-sm font-semibold leading-5 tracking-tight text-neutral-900">
              {{ offer.title }}
            </h3>
            <p class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-neutral-500">
              <span>{{ offer.company || 'Entreprise non précisée' }}</span>
              <span v-if="offer.location">· {{ offer.location }}</span>
            </p>
            <div class="mt-2 flex flex-wrap items-center gap-1.5 text-[10px] text-neutral-500">
              <span v-if="offer.remote" class="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                {{ REMOTE_LABELS[offer.remote] ?? offer.remote }}
              </span>
              <span v-if="offer.contract_type" class="rounded-md bg-neutral-100 px-1.5 py-0.5">
                {{ offer.contract_type }}
              </span>
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">{{ sourceLabel(offer.source) }}</span>
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">
                Publiée le {{ formatDate(offer.published_at) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="offer.score_status === 'filtered'" class="mt-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-[11px] leading-5 text-neutral-600">
          <p class="font-medium text-neutral-700">Offre filtrée avant le LLM</p>
          <ul class="mt-1 list-disc space-y-0.5 pl-4">
            <li v-for="reason in offer.score_reasons" :key="reason">{{ reason }}</li>
          </ul>
        </div>

        <div v-else-if="offer.score_status === 'error'" class="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-[11px] text-rose-700">
          Le scoring a échoué pour cette offre. Relance le scoring.
        </div>

        <div v-else-if="offer.score !== null" class="mt-3 space-y-2">
          <ul class="space-y-1 text-[11px] leading-5 text-neutral-600">
            <li v-for="reason in offer.score_reasons.slice(0, 3)" :key="reason" class="flex gap-1.5">
              <Check :size="12" class="mt-0.5 shrink-0 text-emerald-600" />
              {{ reason }}
            </li>
          </ul>
          <ul v-if="offer.score_blockers.length > 0" class="space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] leading-5 text-amber-800">
            <li v-for="blocker in offer.score_blockers" :key="blocker" class="flex gap-1.5">
              <AlertCircle :size="12" class="mt-0.5 shrink-0" />
              {{ blocker }}
            </li>
          </ul>
        </div>

        <div v-else class="mt-3 text-[11px] text-neutral-400">
          Pas encore scorée. Lance « Scorer 20 offres ».
        </div>

        <div v-if="expanded === offer.id" class="mt-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-[11px] leading-6 text-neutral-600">
          <div v-if="detailsLoading === offer.id" class="flex items-center gap-2 text-neutral-500">
            <LoaderCircle :size="13" class="animate-spin" /> Chargement…
          </div>
          <p v-else class="whitespace-pre-line">
            {{ details[offer.id]?.description?.slice(0, 3000) || 'Description non disponible.' }}
          </p>
        </div>

        <div class="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-neutral-100 pt-4">
          <div class="flex flex-wrap items-center gap-2">
            <select
              :value="offer.status"
              class="rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-[11px] text-neutral-700"
              @change="onStatusChange(offer, $event)"
            >
              <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <button
              type="button"
              class="text-[11px] font-medium text-neutral-500 hover:text-neutral-800"
              @click="toggleDetails(offer)"
            >
              <ChevronUp v-if="expanded === offer.id" :size="12" class="mr-0.5 inline" />
              <ChevronDown v-else :size="12" class="mr-0.5 inline" />
              Détails
            </button>
          </div>

          <div class="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              class="rounded-lg px-2 py-1.5 text-[11px] font-medium text-rose-600 hover:bg-rose-50"
              title="Supprimer et ne plus réafficher"
              @click="deleteOffer(offer)"
            >
              <Trash2 :size="12" class="mr-0.5 inline" />
              Supprimer
            </button>
            <RouterLink
              :to="{ path: '/lettres', query: { offer: offer.id } }"
              class="rounded-lg border border-neutral-200 bg-white px-2.5 py-1.5 text-[11px] font-medium text-neutral-700 hover:bg-neutral-50"
            >
              <FileText :size="12" class="mr-0.5 inline" />
              Lettre
            </RouterLink>
            <a
              v-if="offer.apply_url"
              :href="offer.apply_url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 px-3 py-1.5 text-[11px] font-medium text-white hover:bg-neutral-800"
              @click="markApplied(offer)"
            >
              Postuler
              <ExternalLink :size="11" />
            </a>
          </div>
        </div>
      </article>
    </div>

    <section v-else class="card flex flex-col items-center justify-center px-6 py-16 text-center">
      <div class="grid h-11 w-11 place-items-center rounded-xl bg-neutral-100 text-neutral-400">
        <Search :size="20" />
      </div>
      <p class="mt-3 text-sm font-medium text-neutral-700">Aucune offre ne correspond</p>
      <p class="mt-1 max-w-md text-xs leading-5 text-neutral-500">
        Désactive le filtre campagne, élargis les critères, ou collecte de nouvelles offres depuis la
        page Employeurs.
      </p>
      <div class="mt-4 flex flex-wrap justify-center gap-2">
        <RouterLink to="/employeurs" class="btn-primary">Gérer les employeurs</RouterLink>
        <RouterLink to="/campagne" class="btn-ghost">Modifier la campagne</RouterLink>
      </div>
    </section>

    <!-- Undo toast -->
    <Transition name="fade">
      <div
        v-if="undo"
        class="fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-xl bg-neutral-900 px-4 py-3 text-xs text-white shadow-lift"
      >
        <span class="max-w-xs truncate">« {{ undo.title }} » supprimée.</span>
        <button type="button" class="inline-flex items-center gap-1 font-semibold text-emerald-300 hover:text-emerald-200" @click="restoreOffer">
          <Undo2 :size="13" />
          Annuler
        </button>
      </div>
    </Transition>
  </div>
</template>
