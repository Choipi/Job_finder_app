import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiGet, apiPut } from '@/api/client'
import type { Campaign, CampaignPayload, SourceInfo } from '@/api/types'

export const useCampaignStore = defineStore('campaign', () => {
  const campaign = ref<Campaign | null>(null)
  const sources = ref<SourceInfo[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function load(): Promise<Campaign> {
    loading.value = true
    error.value = null
    try {
      const payload = await apiGet<{ campaign: Campaign }>('/campaign')
      campaign.value = payload.campaign
      return payload.campaign
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function loadSources(): Promise<SourceInfo[]> {
    try {
      const payload = await apiGet<{ sources: SourceInfo[] }>('/sources')
      sources.value = payload.sources
      return payload.sources
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    }
  }

  async function save(values: CampaignPayload): Promise<Campaign> {
    saving.value = true
    error.value = null
    try {
      const payload = await apiPut<{ campaign: Campaign }>('/campaign', values)
      campaign.value = payload.campaign
      return payload.campaign
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      saving.value = false
    }
  }

  async function saveModels(values: {
    scoring_model: string
    letter_model: string
  }): Promise<Campaign> {
    saving.value = true
    error.value = null
    try {
      const payload = await apiPut<{ campaign: Campaign }>('/campaign/models', values)
      campaign.value = payload.campaign
      return payload.campaign
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      saving.value = false
    }
  }

  return {
    campaign,
    sources,
    loading,
    saving,
    error,
    load,
    loadSources,
    save,
    saveModels,
  }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
