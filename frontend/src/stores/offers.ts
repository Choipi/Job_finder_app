import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from '@/api/client'
import type {
  CampaignFilter,
  ManualOfferPayload,
  OfferDetail,
  OfferStats,
  OfferStatus,
  OfferSummary,
  ScoringSummary,
} from '@/api/types'

export const useOffersStore = defineStore('offers', () => {
  const offers = ref<OfferSummary[]>([])
  const total = ref(0)
  const stats = ref<OfferStats | null>(null)
  const campaignFilter = ref<CampaignFilter | null>(null)
  const loading = ref(false)
  const scoring = ref(false)
  const saving = ref(false)
  const creating = ref(false)
  const error = ref<string | null>(null)

  async function load(
    params: {
      q?: string
      remote?: string
      status?: string
      minScore?: number
      sort?: 'score' | 'date'
      limit?: number
      campaign?: boolean
    } = {},
  ): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const search = new URLSearchParams()
      search.set('limit', String(params.limit ?? 100))
      if (params.q) search.set('q', params.q)
      if (params.remote) search.set('remote', params.remote)
      if (params.status) search.set('status', params.status)
      if (params.minScore !== undefined && params.minScore > 0) {
        search.set('min_score', String(params.minScore))
      }
      if (params.sort) search.set('sort', params.sort)
      if (params.campaign) search.set('campaign', '1')
      const payload = await apiGet<{
        offers: OfferSummary[]
        total: number
        stats: OfferStats
        campaign_filter: CampaignFilter
      }>(`/offers?${search.toString()}`)
      offers.value = payload.offers
      total.value = payload.total
      stats.value = payload.stats
      campaignFilter.value = payload.campaign_filter
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function getDetail(id: number): Promise<OfferDetail> {
    const payload = await apiGet<{ offer: OfferDetail }>(`/offers/${id}`)
    return payload.offer
  }

  async function updateStatus(id: number, status: OfferStatus): Promise<void> {
    saving.value = true
    try {
      const payload = await apiPatch<{ offer: OfferDetail }>(`/offers/${id}`, { status })
      const index = offers.value.findIndex((offer) => offer.id === id)
      if (index !== -1) {
        offers.value[index] = { ...offers.value[index], ...payload.offer }
      }
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      saving.value = false
    }
  }

  async function remove(id: number): Promise<void> {
    try {
      await apiDelete<{ deleted: boolean }>(`/offers/${id}`)
      offers.value = offers.value.filter((offer) => offer.id !== id)
      total.value = Math.max(total.value - 1, 0)
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    }
  }

  async function restore(id: number): Promise<void> {
    try {
      await apiPost<{ offer: OfferDetail }>(`/offers/${id}/restore`, {})
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    }
  }

  async function score(limit = 20): Promise<ScoringSummary> {
    scoring.value = true
    error.value = null
    try {
      const payload = await apiPost<{ scoring: ScoringSummary }>(
        '/offers/score',
        { limit },
        300_000,
      )
      return payload.scoring
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      scoring.value = false
    }
  }

  async function createManual(
    payload: ManualOfferPayload,
  ): Promise<{ offer: OfferDetail; created: boolean }> {
    creating.value = true
    error.value = null
    try {
      return await apiPost<{ offer: OfferDetail; created: boolean }>(
        '/offers',
        payload,
        60_000,
      )
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      creating.value = false
    }
  }

  return {
    offers,
    total,
    stats,
    campaignFilter,
    loading,
    scoring,
    saving,
    creating,
    error,
    load,
    getDetail,
    updateStatus,
    remove,
    restore,
    score,
    createManual,
  }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
