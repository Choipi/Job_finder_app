<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { AlertCircle, AlertTriangle, Check, LoaderCircle, Save } from '@lucide/vue'
import { RouterLink } from 'vue-router'

import { ApiError } from '@/api/client'
import type { Campaign, CampaignPayload, CampaignStatus } from '@/api/types'
import FormSection from '@/components/FormSection.vue'
import StatusPill from '@/components/StatusPill.vue'
import TagInput from '@/components/TagInput.vue'
import { messageOf, useCampaignStore } from '@/stores/campaign'

type PillTone = 'ok' | 'warn' | 'error' | 'muted'

interface CampaignForm extends Omit<CampaignPayload, 'starts_on' | 'ends_on'> {
  starts_on: string
  ends_on: string
}

const store = useCampaignStore()

const CONTRACT_TYPES = ['CDI', 'CDD', 'Freelance', 'Stage', 'Alternance', 'Intérim'] as const

const REMOTE_OPTIONS = [
  { value: 'any', label: 'Peu importe' },
  { value: 'onsite', label: 'Sur site uniquement' },
  { value: 'hybrid', label: 'Hybride' },
  { value: 'remote', label: 'Télétravail complet' },
] as const

const FREQUENCY_OPTIONS = [
  { value: 1, label: 'Toutes les heures' },
  { value: 3, label: 'Toutes les 3 heures' },
  { value: 6, label: 'Toutes les 6 heures' },
  { value: 12, label: 'Deux fois par jour' },
  { value: 24, label: 'Une fois par jour' },
  { value: 48, label: 'Tous les deux jours' },
  { value: 168, label: 'Une fois par semaine' },
]

const STATUS_META: Record<CampaignStatus, { label: string; tone: PillTone }> = {
  draft: { label: 'Brouillon', tone: 'muted' },
  scheduled: { label: 'Planifiée', tone: 'warn' },
  active: { label: 'Active', tone: 'ok' },
  paused: { label: 'En pause', tone: 'warn' },
  finished: { label: 'Terminée', tone: 'muted' },
}

const form = reactive<CampaignForm>(blankCampaign())
const initial = ref(snapshot())
const fieldErrors = ref<Record<string, string>>({})
const feedback = ref<{ tone: 'ok' | 'error'; text: string } | null>(null)

function localIsoDate(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

function blankCampaign(): CampaignForm {
  const today = new Date()
  const inThirtyDays = new Date(today.getTime() + 30 * 86_400_000)
  return {
    name: 'Ma recherche',
    keywords: [],
    locations: [],
    contract_types: ['CDI'],
    remote: 'any',
    radius_km: 30,
    sources: [],
    starts_on: localIsoDate(today),
    ends_on: localIsoDate(inThirtyDays),
    frequency_hours: 6,
    is_paused: false,
    score_threshold: 0,
    scoring_model: '',
    letter_model: '',
  }
}

function snapshot(): string {
  return JSON.stringify({ ...form })
}

function applyCampaign(campaign: Campaign): void {
  Object.assign(form, {
    name: campaign.name,
    keywords: [...campaign.keywords],
    locations: [...campaign.locations],
    contract_types: [...campaign.contract_types],
    remote: campaign.remote,
    radius_km: campaign.radius_km,
    sources: [...campaign.sources],
    starts_on: campaign.starts_on ?? '',
    ends_on: campaign.ends_on ?? '',
    frequency_hours: campaign.frequency_hours,
    is_paused: campaign.is_paused,
    score_threshold: campaign.score_threshold,
    scoring_model: campaign.scoring_model,
    letter_model: campaign.letter_model,
  })
  initial.value = snapshot()
}

const dirty = computed(() => snapshot() !== initial.value)

const localStatus = computed<CampaignStatus>(() => {
  if (form.is_paused) return 'paused'
  if (!form.starts_on || !form.ends_on) return 'draft'
  const today = localIsoDate(new Date())
  if (today < form.starts_on) return 'scheduled'
  if (today > form.ends_on) return 'finished'
  return 'active'
})

const durationDays = computed<number | null>(() => {
  if (!form.starts_on || !form.ends_on) return null
  const start = Date.parse(`${form.starts_on}T00:00:00`)
  const end = Date.parse(`${form.ends_on}T00:00:00`)
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null
  return Math.round((end - start) / 86_400_000)
})

const daysRemaining = computed<number | null>(() => {
  if (!form.ends_on) return null
  const end = Date.parse(`${form.ends_on}T00:00:00`)
  if (Number.isNaN(end)) return null
  const today = Date.parse(`${localIsoDate(new Date())}T00:00:00`)
  return Math.max(Math.round((end - today) / 86_400_000), 0)
})

const statusText = computed(() => {
  if (store.loading) return 'Chargement de la campagne…'
  if (store.saving) return 'Enregistrement…'
  if (dirty.value) return 'Modifications non enregistrées'
  return 'Campagne à jour'
})

const statusDot = computed(() => {
  if (store.loading || store.saving || dirty.value) return 'bg-amber-400'
  return 'bg-emerald-500'
})

function notify(tone: 'ok' | 'error', text: string): void {
  feedback.value = { tone, text }
  window.setTimeout(() => {
    if (feedback.value?.text === text) {
      feedback.value = null
    }
  }, 4500)
}

async function load(): Promise<void> {
  try {
    const [campaign] = await Promise.all([store.load(), store.loadSources()])
    applyCampaign(campaign)
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

function reset(): void {
  Object.assign(form, JSON.parse(initial.value) as CampaignForm)
  fieldErrors.value = {}
}

async function save(): Promise<void> {
  fieldErrors.value = {}
  try {
    applyCampaign(await store.save({ ...form }))
    notify('ok', 'Campagne enregistrée.')
  } catch (cause) {
    if (cause instanceof ApiError) {
      fieldErrors.value = cause.fields
    }
    notify('error', messageOf(cause))
  }
}

function toggleValue(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
}

function toggleContract(value: string): void {
  form.contract_types = toggleValue(form.contract_types, value)
}

function toggleSource(value: string): void {
  form.sources = toggleValue(form.sources, value)
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <!-- Save bar -->
    <div class="card flex flex-wrap items-center justify-between gap-3 px-5 py-4">
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-2.5">
          <span class="h-2 w-2 rounded-full" :class="statusDot" />
          <p class="text-sm text-neutral-600">{{ statusText }}</p>
        </div>
        <StatusPill :tone="STATUS_META[localStatus].tone" :label="STATUS_META[localStatus].label" />
        <span v-if="daysRemaining !== null" class="text-xs text-neutral-500">
          {{ daysRemaining }} jour{{ daysRemaining > 1 ? 's' : '' }} restant{{ daysRemaining > 1 ? 's' : '' }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button type="button" class="btn-ghost" :disabled="!dirty || store.saving" @click="reset">
          Annuler
        </button>
        <button type="button" class="btn-primary" :disabled="!dirty || store.saving" @click="save">
          <LoaderCircle v-if="store.saving" :size="16" class="animate-spin" />
          <Save v-else :size="16" />
          Enregistrer
        </button>
      </div>
    </div>

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

    <FormSection
      title="Recherche"
      description="Le profil décrit qui tu es ; la campagne décrit ce que tu cherches et pendant combien de temps."
    >
      <div class="space-y-5">
        <div>
          <label class="field-label" for="campaign_name">Nom de la campagne</label>
          <input id="campaign_name" v-model="form.name" class="input" type="text" maxlength="120" />
          <p v-if="fieldErrors.name" class="field-error">{{ fieldErrors.name }}</p>
        </div>

        <div class="grid gap-5 lg:grid-cols-2">
          <div>
            <label class="field-label">Mots-clés</label>
            <TagInput v-model="form.keywords" :max="20" placeholder="python, data, product…" />
            <p class="field-hint">Appuie sur Entrée après chaque mot-clé. Un seul suffit pour démarrer.</p>
            <p v-if="fieldErrors.keywords" class="field-error">{{ fieldErrors.keywords }}</p>
          </div>

          <div>
            <label class="field-label">Lieux</label>
            <TagInput v-model="form.locations" :max="15" placeholder="Bordeaux, Paris, Remote…" />
            <p class="field-hint">Laisse vide pour chercher partout. « Remote » est accepté comme lieu.</p>
            <p v-if="fieldErrors.locations" class="field-error">{{ fieldErrors.locations }}</p>
          </div>
        </div>

        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <label class="field-label" for="radius">Rayon autour des lieux</label>
            <div class="relative">
              <input id="radius" v-model.number="form.radius_km" class="input pr-12" type="number" min="0" max="200" step="5" />
              <span class="pointer-events-none absolute inset-y-0 right-3.5 grid place-items-center text-xs text-neutral-400">km</span>
            </div>
            <p v-if="fieldErrors.radius_km" class="field-error">{{ fieldErrors.radius_km }}</p>
          </div>

          <div>
            <label class="field-label" for="remote">Télétravail</label>
            <select id="remote" v-model="form.remote" class="select">
              <option v-for="option in REMOTE_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <p v-if="fieldErrors.remote" class="field-error">{{ fieldErrors.remote }}</p>
          </div>
        </div>

        <div>
          <p class="field-label">Types de contrat</p>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="contract in CONTRACT_TYPES"
              :key="contract"
              class="inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-colors"
              :class="
                form.contract_types.includes(contract)
                  ? 'border-neutral-900 bg-neutral-900 text-white'
                  : 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300'
              "
            >
              <input
                type="checkbox"
                class="sr-only"
                :checked="form.contract_types.includes(contract)"
                @change="toggleContract(contract)"
              />
              {{ contract }}
            </label>
          </div>
          <p v-if="fieldErrors.contract_types" class="field-error">{{ fieldErrors.contract_types }}</p>
        </div>
      </div>
    </FormSection>

    <FormSection
      title="Période &amp; rythme"
      description="La collecte tourne entre ces deux dates. À la fin, les offres restent consultables mais le scan s’arrête."
    >
      <div class="space-y-5">
        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <label class="field-label" for="starts_on">Début</label>
            <input id="starts_on" v-model="form.starts_on" class="input" type="date" />
            <p v-if="fieldErrors.starts_on" class="field-error">{{ fieldErrors.starts_on }}</p>
          </div>

          <div>
            <label class="field-label" for="ends_on">Fin</label>
            <input id="ends_on" v-model="form.ends_on" class="input" type="date" />
            <p v-if="fieldErrors.ends_on" class="field-error">{{ fieldErrors.ends_on }}</p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs text-neutral-500">
          <span v-if="durationDays !== null" class="rounded-full bg-neutral-100 px-2.5 py-1 font-medium text-neutral-600">
            {{ durationDays }} jour{{ durationDays > 1 ? 's' : '' }} de campagne
          </span>
          <span>Maximum 365 jours.</span>
        </div>

        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <label class="field-label" for="frequency">Fréquence de scan</label>
            <select id="frequency" v-model.number="form.frequency_hours" class="select">
              <option v-for="option in FREQUENCY_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <p class="field-hint">Le scan automatique sera branché en phase 6 ; ce réglage est déjà enregistré.</p>
            <p v-if="fieldErrors.frequency_hours" class="field-error">{{ fieldErrors.frequency_hours }}</p>
          </div>

          <div class="flex items-start">
            <label class="flex cursor-pointer items-start gap-3 rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
              <input v-model="form.is_paused" type="checkbox" class="mt-0.5 h-4 w-4 accent-emerald-600" />
              <span>
                <span class="block text-sm font-medium text-neutral-800">Mettre la campagne en pause</span>
                <span class="mt-0.5 block text-xs leading-5 text-neutral-500">
                  Les dates et les offres sont conservées, seul le scan est suspendu.
                </span>
              </span>
            </label>
          </div>
        </div>
      </div>
    </FormSection>

    <FormSection
      title="Sources"
      description="Chaque source est un connecteur indépendant. Les APIs officielles sont prioritaires ; les scrapers peuvent casser et se désactivent en un clic."
    >
      <div class="grid gap-3 sm:grid-cols-2">
        <label
          v-for="source in store.sources"
          :key="source.id"
          class="flex cursor-pointer gap-3 rounded-xl border p-3.5 transition-colors"
          :class="
            form.sources.includes(source.id)
              ? 'border-neutral-900 bg-neutral-50/70'
              : 'border-neutral-200 bg-white hover:border-neutral-300'
          "
        >
          <input
            type="checkbox"
            class="mt-0.5 h-4 w-4 shrink-0 accent-emerald-600"
            :checked="form.sources.includes(source.id)"
            @change="toggleSource(source.id)"
          />
          <span class="min-w-0">
            <span class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-medium text-neutral-900">{{ source.label }}</span>
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
                {{ source.kind === 'api' ? 'API' : 'Scraping' }}
              </span>
              <span class="text-[10px] font-medium text-neutral-400">Phase {{ source.phase }}</span>
            </span>
            <span class="mt-1 block text-xs leading-5 text-neutral-500">{{ source.note }}</span>
            <span
              v-if="source.warning"
              class="mt-1.5 flex items-start gap-1.5 text-[11px] leading-4 text-amber-700"
            >
              <AlertTriangle :size="12" class="mt-0.5 shrink-0" />
              {{ source.warning }}
            </span>
          </span>
        </label>
      </div>
      <p v-if="store.sources.length === 0" class="field-hint">Chargement du catalogue…</p>
      <p v-if="fieldErrors.sources" class="field-error">{{ fieldErrors.sources }}</p>
      <p class="field-hint">
        Les job boards ci-dessus seront branchés en phase 5 ; ils sont optionnels. Les offres
        actuelles proviennent des employeurs suivis.
      </p>
      <RouterLink
        to="/employeurs"
        class="mt-2 inline-flex text-xs font-medium text-emerald-700 hover:text-emerald-800"
      >
        Gérer la watchlist d’employeurs →
      </RouterLink>
    </FormSection>

    <FormSection
      title="Pertinence"
      description="Toutes les offres seront affichées et triées par score. Le seuil ci-dessous est un filtre d’affichage optionnel, désactivé par défaut."
    >
      <div>
        <div class="flex items-center justify-between">
          <label class="field-label mb-0" for="score_threshold">Seuil d’affichage</label>
          <span class="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold tabular-nums text-neutral-700">
            {{ form.score_threshold === 0 ? 'Tout afficher' : `Score ≥ ${form.score_threshold}` }}
          </span>
        </div>
        <input
          id="score_threshold"
          v-model.number="form.score_threshold"
          type="range"
          min="0"
          max="100"
          step="5"
          class="mt-3 w-full accent-emerald-600"
        />
        <div class="mt-1 flex justify-between text-[11px] text-neutral-400">
          <span>0 · tout afficher</span>
          <span>100 · très strict</span>
        </div>
        <p v-if="fieldErrors.score_threshold" class="field-error">{{ fieldErrors.score_threshold }}</p>
      </div>

      <div class="mt-5 grid gap-3 rounded-xl border border-neutral-200 bg-neutral-50/60 p-4 text-xs sm:grid-cols-2">
        <div>
          <p class="label">Modèle de scoring</p>
          <p class="mt-1 truncate font-mono text-[11px] text-neutral-700">{{ form.scoring_model || '—' }}</p>
        </div>
        <div>
          <p class="label">Modèle de rédaction</p>
          <p class="mt-1 truncate font-mono text-[11px] text-neutral-700">{{ form.letter_model || '—' }}</p>
        </div>
        <p class="text-[11px] leading-5 text-neutral-500 sm:col-span-2">
          Modifiables dans les réglages. Ils retombent sur les valeurs du fichier
          <code class="font-mono">.env</code>.
        </p>
      </div>
    </FormSection>
  </div>
</template>
