import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiGet, apiPatch, apiPost } from '@/api/client'
import type {
  CollectionOutcome,
  CollectionResult,
  DiscoveryResult,
  EmployerSource,
  EmployerStats,
  EmployersResponse,
} from '@/api/types'

export type EmployerAction = 'seed' | 'discover' | 'collect' | 'add' | null

export const useEmployersStore = defineStore('employers', () => {
  const employers = ref<EmployerSource[]>([])
  const stats = ref<EmployerStats | null>(null)
  const loading = ref(false)
  const busy = ref<EmployerAction>(null)
  const error = ref<string | null>(null)

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const payload = await apiGet<EmployersResponse>('/employers?limit=300')
      employers.value = payload.employers
      stats.value = payload.stats
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function seed(): Promise<{ seed: { created: number; updated: number; total: number } }> {
    busy.value = 'seed'
    error.value = null
    try {
      const payload = await apiPost<{ seed: { created: number; updated: number; total: number } }>(
        '/employers/seed',
        {},
        120_000,
      )
      await load()
      return payload
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      busy.value = null
    }
  }

  async function discover(limit = 8): Promise<DiscoveryResult> {
    busy.value = 'discover'
    error.value = null
    try {
      const payload = await apiPost<{ discovery: DiscoveryResult }>(
        '/employers/discover',
        { limit },
        180_000,
      )
      await load()
      return payload.discovery
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      busy.value = null
    }
  }

  async function collect(limit = 5, maxOffers = 50): Promise<CollectionResult> {
    busy.value = 'collect'
    error.value = null
    try {
      const payload = await apiPost<{ collection: CollectionResult }>(
        '/employers/collect',
        { limit, max_offers: maxOffers },
        180_000,
      )
      await load()
      return payload.collection
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      busy.value = null
    }
  }

  async function add(payload: {
    domain: string
    name?: string
    careers_url?: string
  }): Promise<EmployerSource> {
    busy.value = 'add'
    error.value = null
    try {
      const response = await apiPost<{ employer: EmployerSource }>(
        '/employers',
        payload,
        90_000,
      )
      await load()
      return response.employer
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      busy.value = null
    }
  }

  async function toggle(id: number, enabled: boolean): Promise<void> {
    try {
      await apiPatch<{ employer: EmployerSource }>(`/employers/${id}`, { enabled })
      await load()
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    }
  }

  async function collectOne(id: number): Promise<CollectionOutcome> {
    busy.value = 'collect'
    error.value = null
    try {
      const payload = await apiPost<{ collection: CollectionOutcome }>(
        `/employers/${id}/collect`,
        {},
        120_000,
      )
      await load()
      return payload.collection
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      busy.value = null
    }
  }

  return {
    employers,
    stats,
    loading,
    busy,
    error,
    load,
    seed,
    discover,
    collect,
    add,
    toggle,
    collectOne,
  }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
