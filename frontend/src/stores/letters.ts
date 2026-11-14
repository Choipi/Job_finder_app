import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiDelete, apiGet, apiPost, apiPut } from '@/api/client'
import type {
  GeneratedLetter,
  GeneratedLetterSummary,
  LetterPayload,
  LetterResponse,
} from '@/api/types'

export const useLettersStore = defineStore('letters', () => {
  const history = ref<GeneratedLetterSummary[]>([])
  const current = ref<GeneratedLetter | null>(null)
  const loading = ref(false)
  const generating = ref(false)
  const saving = ref(false)
  const deleting = ref(false)
  const error = ref<string | null>(null)

  async function loadHistory(): Promise<void> {
    loading.value = true
    try {
      const payload = await apiGet<{ letters: GeneratedLetterSummary[]; total: number }>(
        '/letters?limit=30',
      )
      history.value = payload.letters
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function generate(payload: LetterPayload): Promise<LetterResponse> {
    generating.value = true
    error.value = null
    try {
      const response = await apiPost<LetterResponse>('/letters', payload)
      current.value = response.letter
      history.value = [toSummary(response.letter), ...history.value].slice(0, 30)
      return response
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      generating.value = false
    }
  }

  async function select(id: number): Promise<void> {
    loading.value = true
    try {
      const payload = await apiGet<{ letter: GeneratedLetter }>(`/letters/${id}`)
      current.value = payload.letter
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function updateCurrent(subject: string, body: string): Promise<void> {
    if (!current.value) {
      return
    }
    saving.value = true
    try {
      const payload = await apiPut<{ letter: GeneratedLetter }>(
        `/letters/${current.value.id}`,
        { subject, body },
      )
      current.value = payload.letter
      const index = history.value.findIndex((item) => item.id === payload.letter.id)
      if (index !== -1) {
        history.value[index] = toSummary(payload.letter)
      }
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      saving.value = false
    }
  }

  async function removeCurrent(): Promise<void> {
    if (!current.value) {
      return
    }
    deleting.value = true
    const id = current.value.id
    try {
      await apiDelete<{ deleted: boolean }>(`/letters/${id}`)
      current.value = null
      history.value = history.value.filter((item) => item.id !== id)
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      deleting.value = false
    }
  }

  return {
    history,
    current,
    loading,
    generating,
    saving,
    deleting,
    error,
    loadHistory,
    generate,
    select,
    updateCurrent,
    removeCurrent,
  }
})

function toSummary(letter: GeneratedLetter): GeneratedLetterSummary {
  return {
    id: letter.id,
    job_title: letter.job_title,
    company: letter.company,
    subject: letter.subject,
    source_url: letter.source_url,
    model: letter.model,
    prompt_tokens: letter.prompt_tokens,
    completion_tokens: letter.completion_tokens,
    cost_usd: letter.cost_usd,
    duration_ms: letter.duration_ms,
    offer_id: letter.offer_id,
    created_at: letter.created_at,
    updated_at: letter.updated_at,
  }
}

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
