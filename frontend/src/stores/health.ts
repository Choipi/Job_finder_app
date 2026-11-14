import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiGet } from '@/api/client'
import type { HealthPayload } from '@/api/types'

export type HealthStatus = 'idle' | 'loading' | 'ok' | 'error'

export const useHealthStore = defineStore('health', () => {
  const status = ref<HealthStatus>('idle')
  const data = ref<HealthPayload | null>(null)
  const error = ref<string | null>(null)
  const lastCheckedAt = ref<Date | null>(null)

  const isOnline = computed(() => status.value === 'ok' && data.value?.status === 'ok')

  async function refresh(): Promise<void> {
    status.value = 'loading'
    error.value = null

    try {
      data.value = await apiGet<HealthPayload>('/health')
      status.value = 'ok'
    } catch (cause) {
      data.value = null
      status.value = 'error'
      error.value =
        cause instanceof ApiError ? cause.message : 'Erreur inattendue lors de l’appel à l’API.'
    } finally {
      lastCheckedAt.value = new Date()
    }
  }

  return { status, data, error, lastCheckedAt, isOnline, refresh }
})
