<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  AlertCircle,
  AlertTriangle,
  Check,
  Cpu,
  KeyRound,
  LoaderCircle,
  PlugZap,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from '@lucide/vue'

import { ApiError } from '@/api/client'
import type { ModelInfo } from '@/api/types'
import FormSection from '@/components/FormSection.vue'
import StatusPill from '@/components/StatusPill.vue'
import { useCampaignStore } from '@/stores/campaign'
import { useHealthStore } from '@/stores/health'
import { useLlmStore } from '@/stores/llm'

const health = useHealthStore()
const campaign = useCampaignStore()
const llm = useLlmStore()

const scoringModel = ref('')
const letterModel = ref('')
const testModel = ref('')
const savedModels = ref({ scoring: '', letter: '' })
const saving = ref(false)
const fieldErrors = ref<Record<string, string>>({})
const feedback = ref<{ tone: 'ok' | 'error'; text: string } | null>(null)

const llmConfig = computed(() => health.data?.llm)
const isMock = computed(() => health.data?.llm.mock ?? false)
const isReady = computed(() => health.data?.llm.ready ?? false)

const statusTone = computed(() => (isMock.value ? 'warn' : isReady.value ? 'ok' : 'warn'))
const statusLabel = computed(() =>
  isMock.value ? 'Mode démo' : isReady.value ? 'Prêt' : 'À configurer',
)

const modelsDirty = computed(
  () =>
    scoringModel.value !== savedModels.value.scoring ||
    letterModel.value !== savedModels.value.letter,
)

const totals = computed(() => llm.usage?.totals ?? null)

onMounted(async () => {
  try {
    await Promise.all([health.refresh(), campaign.load(), llm.loadAll()])
    const current = campaign.campaign
    scoringModel.value = current?.scoring_model || llm.defaults?.scoring || ''
    letterModel.value = current?.letter_model || llm.defaults?.letter || ''
    testModel.value = letterModel.value
    savedModels.value = { scoring: scoringModel.value, letter: letterModel.value }
  } catch (cause) {
    notify('error', messageOf(cause))
  }
})

function notify(tone: 'ok' | 'error', text: string): void {
  feedback.value = { tone, text }
  window.setTimeout(() => {
    if (feedback.value?.text === text) {
      feedback.value = null
    }
  }, 5000)
}

function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}

function modelLabel(model: ModelInfo): string {
  if (model.free) {
    return `${model.label} — gratuit`
  }
  return `${model.label} — $${model.pricing.input_per_million} / $${model.pricing.output_per_million} par M`
}

async function saveModels(): Promise<void> {
  fieldErrors.value = {}
  saving.value = true
  try {
    const updated = await campaign.saveModels({
      scoring_model: scoringModel.value,
      letter_model: letterModel.value,
    })
    savedModels.value = {
      scoring: updated.scoring_model,
      letter: updated.letter_model,
    }
    testModel.value = updated.letter_model
    notify('ok', 'Modèles enregistrés pour la campagne.')
  } catch (cause) {
    if (cause instanceof ApiError) {
      fieldErrors.value = cause.fields
    }
    notify('error', messageOf(cause))
  } finally {
    saving.value = false
  }
}

async function testConnection(): Promise<void> {
  try {
    const result = await llm.runTest(testModel.value)
    notify('ok', `Connexion OK en ${result.duration_ms} ms.`)
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

async function refreshUsage(): Promise<void> {
  try {
    await llm.loadUsage()
    notify('ok', 'Consommation actualisée.')
  } catch (cause) {
    notify('error', messageOf(cause))
  }
}

function formatCost(value: number): string {
  if (value === 0) {
    return '0 $'
  }
  if (value < 0.00001) {
    return '< 0,00001 $'
  }
  return `${value.toFixed(5)} $`
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

function taskLabel(task: string): string {
  return (
    {
      letter: 'Lettre',
      test: 'Test',
      scoring: 'Scoring',
    }[task] ?? task
  )
}

function statusClass(status: string): string {
  return status === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
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

    <!-- Connection -->
    <FormSection
      title="Connexion OpenCode Go"
      description="La clé reste côté serveur. Le navigateur ne reçoit qu’un état de configuration, jamais sa valeur."
    >
      <template #aside>
        <StatusPill :tone="statusTone" :label="statusLabel" />
      </template>

      <dl class="grid gap-4 sm:grid-cols-2">
        <div>
          <dt class="label">Fournisseur</dt>
          <dd class="mt-1 font-mono text-xs text-neutral-700">{{ llmConfig?.provider ?? '—' }}</dd>
        </div>
        <div>
          <dt class="label">URL de base</dt>
          <dd class="mt-1">
            <StatusPill
              :tone="llmConfig?.base_url_configured ? 'ok' : 'warn'"
              :label="llmConfig?.base_url_configured ? 'Renseignée' : 'Manquante'"
            />
          </dd>
        </div>
        <div>
          <dt class="label">Clé API</dt>
          <dd class="mt-1">
            <StatusPill
              :tone="llmConfig?.configured ? 'ok' : isMock ? 'muted' : 'warn'"
              :label="
                llmConfig?.configured
                  ? 'Détectée côté serveur'
                  : isMock
                    ? 'Non requise en mode démo'
                    : 'Absente'
              "
            />
          </dd>
        </div>
        <div>
          <dt class="label">Mode</dt>
          <dd class="mt-1 flex items-center gap-1.5 text-xs text-neutral-700">
            <ShieldCheck v-if="!isMock" :size="14" class="text-emerald-600" />
            <Sparkles v-else :size="14" class="text-amber-600" />
            {{ isMock ? 'Réponses simulées, aucun appel réseau' : 'Appels réels au fournisseur' }}
          </dd>
        </div>
      </dl>

      <div
        v-if="isMock"
        class="mt-5 flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs leading-5 text-amber-800"
      >
        <AlertTriangle :size="16" class="mt-0.5 shrink-0" />
        <p>
          <code class="font-mono">LLM_PROVIDER=mock</code> est actif : les lettres sont générées
          localement. Retire cette variable (ou mets <code class="font-mono">opencode_go</code>)
          pour utiliser le vrai modèle.
        </p>
      </div>

      <div
        v-else-if="!isReady"
        class="mt-5 flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs leading-5 text-amber-800"
      >
        <KeyRound :size="16" class="mt-0.5 shrink-0" />
        <p>
          Renseigne <code class="font-mono">OPENCODE_API_KEY</code> dans
          <code class="font-mono">.env</code>, puis redémarre Flask. Les appels resteront bloqués
          en attendant.
        </p>
      </div>

      <div class="mt-5 border-t border-neutral-100 pt-5">
        <p class="field-label">Tester la connexion</p>
        <div class="flex flex-col gap-2 sm:flex-row">
          <select v-model="testModel" class="select sm:flex-1">
            <option v-for="model in llm.models" :key="model.id" :value="model.id">
              {{ modelLabel(model) }}
            </option>
          </select>
          <button type="button" class="btn-ghost shrink-0" :disabled="llm.testing" @click="testConnection">
            <LoaderCircle v-if="llm.testing" :size="15" class="animate-spin" />
            <PlugZap v-else :size="15" />
            {{ llm.testing ? 'Test en cours…' : 'Tester' }}
          </button>
        </div>
        <p class="field-hint">Envoie un prompt minuscule (« Réponds OK ») et vérifie le couple clé / endpoint / modèle.</p>

        <div
          v-if="llm.testResult"
          class="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-800"
        >
          <p class="font-medium">
            Réponse : « {{ llm.testResult.reply }} » · {{ llm.testResult.duration_ms }} ms
          </p>
          <p class="mt-1 text-emerald-700">
            {{ llm.testResult.model }} · {{ llm.testResult.usage.prompt_tokens }} +
            {{ llm.testResult.usage.completion_tokens }} tokens ·
            {{ formatCost(llm.testResult.usage.cost_usd) }}
          </p>
        </div>
      </div>
    </FormSection>

    <!-- Models -->
    <FormSection
      title="Modèles par tâche"
      description="Un modèle rapide et bon marché suffit pour juger une offre. La rédaction mérite un modèle plus soigné. Les tarifs sont indicatifs, par million de tokens."
    >
      <div class="grid gap-5 lg:grid-cols-2">
        <div>
          <label class="field-label" for="scoring_model">Scoring des offres</label>
          <select id="scoring_model" v-model="scoringModel" class="select">
            <option v-for="model in llm.models" :key="model.id" :value="model.id">
              {{ modelLabel(model) }}
            </option>
          </select>
          <p class="field-hint">Utilisé à partir de la phase 6, pour noter les annonces.</p>
          <p v-if="fieldErrors.scoring_model" class="field-error">{{ fieldErrors.scoring_model }}</p>
        </div>

        <div>
          <label class="field-label" for="letter_model">Rédaction des lettres</label>
          <select id="letter_model" v-model="letterModel" class="select">
            <option v-for="model in llm.models" :key="model.id" :value="model.id">
              {{ modelLabel(model) }}
            </option>
          </select>
          <p class="field-hint">Utilisé dès maintenant sur la page Lettres.</p>
          <p v-if="fieldErrors.letter_model" class="field-error">{{ fieldErrors.letter_model }}</p>
        </div>
      </div>

      <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-4">
        <p class="text-xs text-neutral-500">
          Enregistré dans la campagne active. Une estimation de coût est calculée à chaque appel.
        </p>
        <button type="button" class="btn-primary" :disabled="!modelsDirty || saving" @click="saveModels">
          <LoaderCircle v-if="saving" :size="15" class="animate-spin" />
          <Cpu v-else :size="15" />
          Enregistrer les modèles
        </button>
      </div>
    </FormSection>

    <!-- Usage -->
    <FormSection
      title="Consommation"
      description="Chaque appel est journalisé en base avec son modèle, ses tokens, sa latence et un coût estimé."
    >
      <template #aside>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-600 transition-colors hover:text-neutral-900"
          @click="refreshUsage"
        >
          <RefreshCw :size="13" :class="llm.loading ? 'animate-spin' : ''" />
          Actualiser
        </button>
      </template>

      <div v-if="totals" class="grid gap-3 sm:grid-cols-3">
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">Appels</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">{{ totals.calls.toLocaleString('fr-FR') }}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">Tokens</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">{{ totals.total_tokens.toLocaleString('fr-FR') }}</p>
          <p class="mt-0.5 text-[11px] text-neutral-500">
            {{ totals.prompt_tokens.toLocaleString('fr-FR') }} entrée ·
            {{ totals.completion_tokens.toLocaleString('fr-FR') }} sortie
          </p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4">
          <p class="label">Coût estimé</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">{{ formatCost(totals.cost_usd) }}</p>
          <p class="mt-0.5 text-[11px] text-neutral-500">Hors cache et heures pleines.</p>
        </div>
      </div>

      <div class="mt-5 overflow-x-auto rounded-xl border border-neutral-200">
        <table class="w-full min-w-[640px] text-left text-xs">
          <thead class="bg-neutral-50 text-neutral-500">
            <tr>
              <th class="px-3 py-2 font-medium">Tâche</th>
              <th class="px-3 py-2 font-medium">Modèle</th>
              <th class="px-3 py-2 font-medium">Statut</th>
              <th class="px-3 py-2 text-right font-medium">Tokens</th>
              <th class="px-3 py-2 text-right font-medium">Durée</th>
              <th class="px-3 py-2 text-right font-medium">Coût</th>
              <th class="px-3 py-2 text-right font-medium">Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="call in llm.usage?.recent ?? []" :key="call.id" class="text-neutral-700">
              <td class="px-3 py-2">{{ taskLabel(call.task) }}</td>
              <td class="px-3 py-2 font-mono text-[11px]">{{ call.model }}</td>
              <td class="px-3 py-2">
                <span
                  class="rounded-md px-1.5 py-0.5 text-[10px] font-medium"
                  :class="statusClass(call.status)"
                >
                  {{ call.status === 'ok' ? 'OK' : 'Erreur' }}
                </span>
              </td>
              <td class="px-3 py-2 text-right tabular-nums">
                {{ (call.prompt_tokens + call.completion_tokens).toLocaleString('fr-FR') }}
              </td>
              <td class="px-3 py-2 text-right tabular-nums">{{ (call.duration_ms / 1000).toFixed(1) }} s</td>
              <td class="px-3 py-2 text-right tabular-nums">{{ formatCost(call.cost_usd) }}</td>
              <td class="px-3 py-2 text-right text-neutral-500">{{ formatDate(call.created_at) }}</td>
            </tr>
            <tr v-if="(llm.usage?.recent.length ?? 0) === 0">
              <td colspan="7" class="px-3 py-8 text-center text-neutral-500">
                Aucun appel enregistré. Lance un test de connexion ou génère une lettre.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="field-hint">
        Les erreurs sont conservées avec leur message. Documentation pédagogique :
        <code class="font-mono">docs/llm.md</code>.
      </p>
    </FormSection>
  </div>
</template>
