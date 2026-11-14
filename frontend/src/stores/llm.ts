import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiGet, apiPost } from '@/api/client'
import type { LlmTestResult, LlmUsage, ModelInfo, ModelsResponse } from '@/api/types'

export const useLlmStore = defineStore('llm', () => {
  const models = ref<ModelInfo[]>([])
  const usage = ref<LlmUsage | null>(null)
  const defaults = ref<{ scoring: string; letter: string } | null>(null)
  const testResult = ref<LlmTestResult | null>(null)
  const loading = ref(false)
  const testing = ref(false)
  const error = ref<string | null>(null)

  async function loadModels(): Promise<void> {
    const payload = await apiGet<ModelsResponse>('/models')
    models.value = payload.models
    defaults.value = payload.defaults
  }

  async function loadUsage(): Promise<void> {
    usage.value = await apiGet<LlmUsage>('/llm/usage')
  }

  async function loadAll(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await Promise.all([loadModels(), loadUsage()])
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function runTest(model: string): Promise<LlmTestResult> {
    testing.value = true
    error.value = null
    testResult.value = null
    try {
      testResult.value = await apiPost<LlmTestResult>('/llm/test', { model })
      await loadUsage()
      return testResult.value
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      testing.value = false
    }
  }

  return {
    models,
    usage,
    defaults,
    testResult,
    loading,
    testing,
    error,
    loadModels,
    loadUsage,
    loadAll,
    runTest,
  }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
