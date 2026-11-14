<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { AlertCircle, Check, FileText, LoaderCircle, Save, Trash2, UploadCloud } from '@lucide/vue'

import { ApiError } from '@/api/client'
import type { Profile, ProfilePayload } from '@/api/types'
import FormSection from '@/components/FormSection.vue'
import { messageOf, useProfileStore } from '@/stores/profile'

const store = useProfileStore()

const form = reactive<ProfilePayload>(blankProfile())
const initial = ref(snapshot())
const fieldErrors = ref<Record<string, string>>({})
const feedback = ref<{ tone: 'ok' | 'error'; text: string } | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const dragActive = ref(false)
const removingCv = ref(false)

function blankProfile(): ProfilePayload {
  return {
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    city: '',
    headline: '',
    summary: '',
    cv_text: '',
    letter_template: '',
  }
}

function snapshot(): string {
  return JSON.stringify({ ...form })
}

function applyProfile(profile: Profile): void {
  Object.assign(form, {
    first_name: profile.first_name,
    last_name: profile.last_name,
    email: profile.email,
    phone: profile.phone,
    city: profile.city,
    headline: profile.headline,
    summary: profile.summary,
    cv_text: profile.cv_text,
    letter_template: profile.letter_template,
  })
  initial.value = snapshot()
}

const dirty = computed(() => snapshot() !== initial.value)

const statusText = computed(() => {
  if (store.loading) return 'Chargement du profil…'
  if (store.saving) return 'Enregistrement…'
  if (store.uploading) return 'Import et extraction du CV…'
  if (dirty.value) return 'Modifications non enregistrées'
  return 'Profil à jour'
})

const statusTone = computed(() => {
  if (store.loading || store.saving || store.uploading) return 'bg-amber-400'
  if (dirty.value) return 'bg-amber-400'
  return 'bg-emerald-500'
})

const cvUploadedLabel = computed(() => {
  const value = store.profile?.cv_uploaded_at
  if (!value) return ''
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
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
    applyProfile(await store.load())
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

function reset(): void {
  Object.assign(form, JSON.parse(initial.value) as ProfilePayload)
  fieldErrors.value = {}
}

async function save(): Promise<void> {
  fieldErrors.value = {}
  try {
    applyProfile(await store.save({ ...form }))
    notify('ok', 'Profil enregistré.')
  } catch (cause) {
    if (cause instanceof ApiError) {
      fieldErrors.value = cause.fields
    }
    notify('error', messageOf(cause))
  }
}

function openFilePicker(): void {
  fileInput.value?.click()
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    void uploadFile(file)
  }
  input.value = ''
}

function onDrop(event: DragEvent): void {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    void uploadFile(file)
  }
}

async function uploadFile(file: File): Promise<void> {
  fieldErrors.value = {}
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    fieldErrors.value = { file: 'Choisis un fichier PDF.' }
    return
  }

  try {
    const profile = await store.uploadCv(file)
    applyProfile(profile)
    notify(
      'ok',
      `CV importé : ${profile.cv_text.length.toLocaleString('fr-FR')} caractères extraits.`,
    )
  } catch (cause) {
    if (cause instanceof ApiError) {
      fieldErrors.value = cause.fields
    }
    notify('error', messageOf(cause))
  }
}

async function removeCv(): Promise<void> {
  if (!window.confirm('Supprimer le CV importé et son texte extrait ?')) {
    return
  }

  removingCv.value = true
  try {
    applyProfile(await store.removeCv())
    notify('ok', 'CV supprimé.')
  } catch (cause) {
    notify('error', messageOf(cause))
  } finally {
    removingCv.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <!-- Save bar -->
    <div class="card flex flex-wrap items-center justify-between gap-3 px-5 py-4">
      <div class="flex items-center gap-2.5">
        <span class="h-2 w-2 rounded-full" :class="statusTone" />
        <p class="text-sm text-neutral-600">{{ statusText }}</p>
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
      title="Identité"
      description="Ces informations sont utilisées dans l’en-tête des lettres de motivation."
    >
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="field-label" for="first_name">Prénom</label>
          <input id="first_name" v-model="form.first_name" class="input" type="text" autocomplete="given-name" />
          <p v-if="fieldErrors.first_name" class="field-error">{{ fieldErrors.first_name }}</p>
        </div>

        <div>
          <label class="field-label" for="last_name">Nom</label>
          <input id="last_name" v-model="form.last_name" class="input" type="text" autocomplete="family-name" />
          <p v-if="fieldErrors.last_name" class="field-error">{{ fieldErrors.last_name }}</p>
        </div>

        <div>
          <label class="field-label" for="email">Email</label>
          <input id="email" v-model="form.email" class="input" type="email" autocomplete="email" placeholder="prenom.nom@exemple.fr" />
          <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
        </div>

        <div>
          <label class="field-label" for="phone">Téléphone</label>
          <input id="phone" v-model="form.phone" class="input" type="tel" autocomplete="tel" placeholder="06 12 34 56 78" />
          <p v-if="fieldErrors.phone" class="field-error">{{ fieldErrors.phone }}</p>
        </div>

        <div>
          <label class="field-label" for="city">Ville</label>
          <input id="city" v-model="form.city" class="input" type="text" autocomplete="address-level2" />
          <p v-if="fieldErrors.city" class="field-error">{{ fieldErrors.city }}</p>
        </div>

        <div>
          <label class="field-label" for="headline">Poste visé</label>
          <input id="headline" v-model="form.headline" class="input" type="text" placeholder="Développeuse Python" />
          <p v-if="fieldErrors.headline" class="field-error">{{ fieldErrors.headline }}</p>
        </div>
      </div>
    </FormSection>

    <FormSection
      title="Profil"
      description="Résume ton parcours, tes compétences et ce que tu cherches. Ce texte servira au scoring des offres et à la rédaction."
    >
      <label class="field-label" for="summary">Présentation</label>
      <textarea
        id="summary"
        v-model="form.summary"
        class="textarea"
        rows="6"
        maxlength="5000"
        placeholder="Développeuse back-end, 5 ans d’expérience en Python et Flask. Je cherche un poste en CDI à Bordeaux ou en remote, dans une équipe produit."
      />
      <div class="mt-1.5 flex items-start justify-between gap-4">
        <p class="field-hint">Sois concret : technologies, années d’expérience, secteurs, contraintes.</p>
        <p class="shrink-0 text-[11px] tabular-nums text-neutral-400">{{ form.summary.length }} / 5000</p>
      </div>
      <p v-if="fieldErrors.summary" class="field-error">{{ fieldErrors.summary }}</p>
    </FormSection>

    <FormSection
      title="CV"
      description="Importe ton CV en PDF. Le texte est extrait puis reste modifiable : corrige-le si la mise en page a été mal lue."
    >
      <template #aside>
        <span
          v-if="store.profile?.has_cv_file"
          class="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20"
        >
          <FileText :size="13" />
          {{ store.profile.cv_filename }}
        </span>
      </template>

      <input
        ref="fileInput"
        type="file"
        accept=".pdf,application/pdf"
        class="hidden"
        @change="onFileChange"
      />

      <div
        class="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition"
        :class="
          dragActive
            ? 'border-emerald-400 bg-emerald-50/60'
            : 'border-neutral-200 bg-neutral-50/60 hover:border-neutral-300 hover:bg-neutral-50'
        "
        role="button"
        tabindex="0"
        @click="openFilePicker"
        @keydown.enter.prevent="openFilePicker"
        @keydown.space.prevent="openFilePicker"
        @dragover.prevent="dragActive = true"
        @dragleave.prevent="dragActive = false"
        @drop.prevent="onDrop"
      >
        <LoaderCircle v-if="store.uploading" :size="22" class="animate-spin text-neutral-400" />
        <UploadCloud v-else :size="22" class="text-neutral-400" />
        <p class="mt-2 text-sm font-medium text-neutral-700">
          {{ store.uploading ? 'Extraction en cours…' : 'Dépose ton CV ici ou clique pour choisir un PDF' }}
        </p>
        <p class="mt-1 text-xs text-neutral-500">
          10 Mo maximum · le PDF doit contenir du texte, pas seulement une image.
        </p>
      </div>
      <p v-if="fieldErrors.file" class="field-error">{{ fieldErrors.file }}</p>

      <div class="mt-4 flex items-center justify-between gap-3">
        <p v-if="store.profile?.has_cv_file" class="text-xs text-neutral-500">
          Importé le {{ cvUploadedLabel }}
        </p>
        <button
          v-if="store.profile?.has_cv_file"
          type="button"
          class="inline-flex items-center gap-1.5 text-xs font-medium text-rose-600 transition-colors hover:text-rose-700 disabled:opacity-50"
          :disabled="removingCv"
          @click="removeCv"
        >
          <Trash2 :size="14" />
          Supprimer le CV
        </button>
      </div>

      <div class="mt-5">
        <label class="field-label" for="cv_text">Texte du CV</label>
        <textarea
          id="cv_text"
          v-model="form.cv_text"
          class="textarea font-mono text-[13px]"
          rows="14"
          maxlength="40000"
          placeholder="Importe un PDF ou colle directement le contenu de ton CV ici."
        />
        <div class="mt-1.5 flex items-start justify-between gap-4">
          <p class="field-hint">Ce texte est envoyé au modèle pour rédiger les lettres.</p>
          <p class="shrink-0 text-[11px] tabular-nums text-neutral-400">
            {{ form.cv_text.length.toLocaleString('fr-FR') }} / 40 000
          </p>
        </div>
        <p v-if="fieldErrors.cv_text" class="field-error">{{ fieldErrors.cv_text }}</p>
      </div>
    </FormSection>

    <FormSection
      title="Lettre type"
      description="Une lettre qui te ressemble et dont la structure sera suivie. Le modèle l’adaptera à chaque offre sans inventer d’expérience."
    >
      <label class="field-label" for="letter_template">Modèle de référence</label>
      <textarea
        id="letter_template"
        v-model="form.letter_template"
        class="textarea"
        rows="12"
        maxlength="20000"
        placeholder="Madame, Monsieur,&#10;&#10;Je vous adresse ma candidature pour le poste de …&#10;&#10;Mon parcours de … m’a permis de …&#10;&#10;Je reste à votre disposition pour en échanger.&#10;&#10;Bien cordialement,&#10;Prénom Nom"
      />
      <div class="mt-1.5 flex items-start justify-between gap-4">
        <p class="field-hint">
          Colle une lettre réelle, pas un modèle générique. Le style sera conservé.
        </p>
        <p class="shrink-0 text-[11px] tabular-nums text-neutral-400">
          {{ form.letter_template.length.toLocaleString('fr-FR') }} / 20 000
        </p>
      </div>
      <p v-if="fieldErrors.letter_template" class="field-error">{{ fieldErrors.letter_template }}</p>
    </FormSection>
  </div>
</template>
