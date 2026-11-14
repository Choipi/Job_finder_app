<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import {
  AlertCircle,
  AlertTriangle,
  Check,
  Copy,
  FileText,
  LoaderCircle,
  Save,
  Sparkles,
  Trash2,
} from '@lucide/vue'
import { RouterLink, useRoute } from 'vue-router'

import { apiGet, ApiError } from '@/api/client'
import type { LetterPayload, OfferDetail } from '@/api/types'
import FormSection from '@/components/FormSection.vue'
import { useCampaignStore } from '@/stores/campaign'
import { useLettersStore } from '@/stores/letters'

const letters = useLettersStore()
const campaign = useCampaignStore()
const route = useRoute()

const form = reactive<LetterPayload>({
  job_title: '',
  company: '',
  job_description: '',
  source_url: '',
  instructions: '',
})

const linkedOffer = ref<OfferDetail | null>(null)
const offerId = ref<number | null>(null)

const editing = reactive({ subject: '', body: '' })
const editingInitial = ref('')
const fieldErrors = ref<Record<string, string>>({})
const truncated = ref<string[]>([])
const copied = ref(false)
const resultSection = ref<HTMLElement | null>(null)

const letterModel = computed(() => campaign.campaign?.letter_model ?? '—')

const isDirty = computed(
  () =>
    letters.current !== null &&
    JSON.stringify({ subject: editing.subject, body: editing.body }) !== editingInitial.value,
)

const hasProfileGap = computed(
  () => Boolean(fieldErrors.value.cv_text) || Boolean(fieldErrors.value.letter_template),
)

const TRUNCATED_LABELS: Record<string, string> = {
  summary: 'la présentation',
  cv: 'le CV',
  template: 'la lettre type',
  description: 'la description de l’offre',
  instructions: 'la consigne supplémentaire',
}

watch(
  () => letters.current,
  (letter) => {
    if (!letter) {
      return
    }
    editing.subject = letter.subject
    editing.body = letter.body
    editingInitial.value = JSON.stringify({ ...editing })
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    await Promise.all([letters.loadHistory(), campaign.load()])
    const first = letters.history[0]
    if (first) {
      await letters.select(first.id)
    }
    const queryOffer = Number(route.query.offer)
    if (Number.isInteger(queryOffer) && queryOffer > 0) {
      await loadOffer(queryOffer)
    }
  } catch {
    // The store already holds a readable error.
  }
})

async function loadOffer(id: number): Promise<void> {
  try {
    const payload = await apiGet<{ offer: OfferDetail }>(`/offers/${id}`)
    const offer = payload.offer
    linkedOffer.value = offer
    offerId.value = offer.id
    form.job_title = offer.title
    form.company = offer.company
    form.source_url = offer.source_url || offer.apply_url
    form.job_description = offer.description
    form.instructions = ''
  } catch (cause) {
    letters.error = cause instanceof ApiError ? cause.message : 'Offre introuvable.'
  }
}

function clearError(): void {
  letters.error = null
}

async function generate(): Promise<void> {
  fieldErrors.value = {}
  truncated.value = []
  clearError()

  try {
    const response = await letters.generate({
      ...form,
      offer_id: offerId.value ?? undefined,
    })
    truncated.value = response.context_truncated
    await nextTick()
    resultSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (cause) {
    if (cause instanceof ApiError) {
      fieldErrors.value = cause.fields
    }
  }
}

async function selectLetter(id: number): Promise<void> {
  clearError()
  try {
    await letters.select(id)
    await nextTick()
    resultSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch {
    // Store error is displayed above.
  }
}

async function saveEdits(): Promise<void> {
  clearError()
  try {
    await letters.updateCurrent(editing.subject, editing.body)
    editingInitial.value = JSON.stringify({ ...editing })
  } catch {
    // Store error is displayed above.
  }
}

async function copyLetter(): Promise<void> {
  const text = [editing.subject.trim(), editing.body.trim()].filter(Boolean).join('\n\n')
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    window.setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    letters.error = 'La copie dans le presse-papiers a échoué.'
  }
}

async function deleteLetter(): Promise<void> {
  if (!window.confirm('Supprimer définitivement cette lettre ?')) {
    return
  }
  clearError()
  try {
    await letters.removeCurrent()
    truncated.value = []
  } catch {
    // Store error is displayed above.
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

function formatCost(value: number): string {
  if (value === 0) {
    return 'gratuit'
  }
  if (value < 0.00001) {
    return '< 0,00001 $'
  }
  return `${value.toFixed(5)} $`
}
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-5">
    <div class="space-y-6 lg:col-span-3">
      <Transition name="fade">
        <div
          v-if="letters.error"
          class="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          <AlertCircle :size="16" class="mt-0.5 shrink-0" />
          <p class="flex-1">{{ letters.error }}</p>
          <button type="button" class="text-xs font-medium underline" @click="clearError">
            Fermer
          </button>
        </div>
      </Transition>

      <div
        v-if="linkedOffer"
        class="flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-800"
      >
        <FileText :size="16" class="mt-0.5 shrink-0" />
        <p class="flex-1">
          Lettre liée à <strong>{{ linkedOffer.title }}</strong> chez
          {{ linkedOffer.company }}. Le formulaire est prérempli depuis l’offre.
        </p>
        <RouterLink to="/offres" class="font-medium underline">Voir les offres</RouterLink>
      </div>

      <FormSection
        title="Nouvelle lettre"
        description="Colle le texte de l’offre. Le modèle s’appuie sur ton CV et sur ta lettre type pour produire une version adaptée, sans inventer d’expérience."
      >
        <template #aside>
          <span class="rounded-full bg-neutral-100 px-2.5 py-1 font-mono text-[11px] text-neutral-600">
            {{ letterModel }}
          </span>
        </template>

        <div class="space-y-5">
          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="field-label" for="job_title">Intitulé du poste</label>
              <input
                id="job_title"
                v-model="form.job_title"
                class="input"
                type="text"
                maxlength="200"
                placeholder="Développeur Python Senior"
              />
              <p v-if="fieldErrors.job_title" class="field-error">{{ fieldErrors.job_title }}</p>
            </div>

            <div>
              <label class="field-label" for="company">Entreprise</label>
              <input
                id="company"
                v-model="form.company"
                class="input"
                type="text"
                maxlength="200"
                placeholder="DataForge"
              />
              <p v-if="fieldErrors.company" class="field-error">{{ fieldErrors.company }}</p>
            </div>
          </div>

          <div>
            <label class="field-label" for="source_url">Lien de l’annonce <span class="font-normal text-neutral-400">(optionnel)</span></label>
            <input
              id="source_url"
              v-model="form.source_url"
              class="input"
              type="url"
              maxlength="500"
              placeholder="https://…"
            />
            <p v-if="fieldErrors.source_url" class="field-error">{{ fieldErrors.source_url }}</p>
          </div>

          <div>
            <label class="field-label" for="job_description">Description de l’offre</label>
            <textarea
              id="job_description"
              v-model="form.job_description"
              class="textarea"
              rows="9"
              maxlength="30000"
              placeholder="Colle ici l’annonce complète : missions, technologies, équipe, localisation…"
            />
            <div class="mt-1.5 flex items-start justify-between gap-4">
              <p class="field-hint">Plus l’annonce est complète, plus la lettre sera précise.</p>
              <p class="shrink-0 text-[11px] tabular-nums text-neutral-400">
                {{ form.job_description.length.toLocaleString('fr-FR') }} / 30 000
              </p>
            </div>
            <p v-if="fieldErrors.job_description" class="field-error">
              {{ fieldErrors.job_description }}
            </p>
          </div>

          <div>
            <label class="field-label" for="instructions">
              Consigne supplémentaire <span class="font-normal text-neutral-400">(optionnel)</span>
            </label>
            <textarea
              id="instructions"
              v-model="form.instructions"
              class="textarea"
              rows="2"
              maxlength="1000"
              placeholder="Ex. insiste sur les tests, reste très sobre, mentionne la mobilité…"
            />
            <p v-if="fieldErrors.instructions" class="field-error">{{ fieldErrors.instructions }}</p>
          </div>

          <div
            v-if="hasProfileGap"
            class="flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs leading-5 text-amber-800"
          >
            <AlertTriangle :size="16" class="mt-0.5 shrink-0" />
            <p>
              Le CV ou la lettre type est vide.
              <RouterLink to="/profil" class="font-semibold underline">Compléter le profil</RouterLink>
              avant de générer.
            </p>
          </div>

          <div v-if="fieldErrors.model" class="field-error">{{ fieldErrors.model }}</div>

          <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-4">
            <p class="text-xs text-neutral-500">
              Génération typique : 3 à 15 s. Chaque appel est journalisé avec son coût.
            </p>
            <button type="button" class="btn-primary" :disabled="letters.generating" @click="generate">
              <LoaderCircle v-if="letters.generating" :size="16" class="animate-spin" />
              <Sparkles v-else :size="16" />
              {{ letters.generating ? 'Rédaction…' : 'Générer la lettre' }}
            </button>
          </div>
        </div>
      </FormSection>

      <div ref="resultSection" class="scroll-mt-6">
        <Transition name="fade">
          <div
            v-if="truncated.length > 0"
            class="mb-4 flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs leading-5 text-amber-800"
          >
            <AlertTriangle :size="16" class="mt-0.5 shrink-0" />
            <p>
              Contexte tronqué pour rester dans les limites :
              {{ truncated.map((key) => TRUNCATED_LABELS[key] ?? key).join(', ') }}.
            </p>
          </div>
        </Transition>

        <section v-if="letters.current" class="card overflow-hidden">
          <header class="flex flex-wrap items-start justify-between gap-3 border-b border-neutral-100 px-6 py-4">
            <div class="min-w-0">
              <p class="text-sm font-semibold tracking-tight">
                {{ letters.current.job_title }}
                <span class="font-normal text-neutral-400">·</span>
                {{ letters.current.company }}
              </p>
              <p class="mt-0.5 text-xs text-neutral-500">
                {{ formatDate(letters.current.created_at) }} · {{ letters.current.prompt_version }}
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-1.5 text-[11px] text-neutral-500">
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5 font-mono">{{ letters.current.model }}</span>
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">
                {{ (letters.current.prompt_tokens + letters.current.completion_tokens).toLocaleString('fr-FR') }} tokens
              </span>
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">{{ formatCost(letters.current.cost_usd) }}</span>
              <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">
                {{ (letters.current.duration_ms / 1000).toFixed(1) }} s
              </span>
            </div>
          </header>

          <div class="space-y-4 px-6 py-5">
            <div>
              <label class="field-label" for="letter_subject">Objet</label>
              <input id="letter_subject" v-model="editing.subject" class="input" type="text" maxlength="300" />
            </div>

            <div>
              <label class="field-label" for="letter_body">Lettre</label>
              <textarea
                id="letter_body"
                v-model="editing.body"
                class="textarea font-serif text-[15px] leading-7"
                rows="18"
                maxlength="30000"
              />
              <p class="field-hint">
                Relis et ajuste avant d’envoyer. Le texte reste modifiable et enregistrable.
              </p>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-4">
              <button type="button" class="text-xs font-medium text-rose-600 transition-colors hover:text-rose-700" :disabled="letters.deleting" @click="deleteLetter">
                <Trash2 :size="14" class="mr-1 inline" />
                Supprimer
              </button>

              <div class="flex flex-wrap items-center gap-2">
                <button type="button" class="btn-ghost" @click="copyLetter">
                  <Check v-if="copied" :size="15" class="text-emerald-600" />
                  <Copy v-else :size="15" />
                  {{ copied ? 'Copié' : 'Copier' }}
                </button>
                <button type="button" class="btn-primary" :disabled="!isDirty || letters.saving" @click="saveEdits">
                  <LoaderCircle v-if="letters.saving" :size="15" class="animate-spin" />
                  <Save v-else :size="15" />
                  Enregistrer les modifications
                </button>
              </div>
            </div>
          </div>
        </section>

        <section v-else class="card flex flex-col items-center justify-center px-6 py-14 text-center">
          <div class="grid h-11 w-11 place-items-center rounded-xl bg-neutral-100 text-neutral-400">
            <FileText :size="20" />
          </div>
          <p class="mt-3 text-sm font-medium text-neutral-700">Aucune lettre ouverte</p>
          <p class="mt-1 max-w-sm text-xs leading-5 text-neutral-500">
            Remplis le formulaire et lance une génération, ou sélectionne une lettre dans
            l’historique.
          </p>
        </section>
      </div>
    </div>

    <!-- History -->
    <aside class="lg:col-span-2">
      <section class="card overflow-hidden lg:sticky lg:top-6">
        <header class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
          <div>
            <h2 class="text-sm font-semibold tracking-tight">Historique</h2>
            <p class="mt-0.5 text-xs text-neutral-500">{{ letters.history.length }} lettre(s)</p>
          </div>
          <LoaderCircle v-if="letters.loading" :size="16" class="animate-spin text-neutral-400" />
        </header>

        <div v-if="letters.history.length > 0" class="max-h-[70vh] divide-y divide-neutral-100 overflow-y-auto">
          <button
            v-for="item in letters.history"
            :key="item.id"
            type="button"
            class="block w-full px-5 py-3.5 text-left transition-colors hover:bg-neutral-50"
            :class="letters.current?.id === item.id ? 'bg-neutral-50' : 'bg-white'"
            @click="selectLetter(item.id)"
          >
            <p class="truncate text-sm font-medium text-neutral-800">
              {{ item.subject || item.job_title }}
            </p>
            <p class="mt-0.5 truncate text-xs text-neutral-500">
              {{ item.company }} · {{ formatDate(item.created_at) }}
            </p>
            <p class="mt-1 flex items-center gap-2 text-[11px] text-neutral-400">
              <span class="font-mono">{{ item.model }}</span>
              <span>·</span>
              <span>{{ formatCost(item.cost_usd) }}</span>
            </p>
          </button>
        </div>

        <div v-else class="px-5 py-10 text-center">
          <p class="text-xs leading-5 text-neutral-500">
            Les lettres générées apparaîtront ici, avec leur modèle et leur coût.
          </p>
        </div>
      </section>
    </aside>
  </div>
</template>
