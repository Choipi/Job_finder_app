import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiGet } from '@/api/client'
import type { CampaignFilter, OfferDetail, OfferSummary } from '@/api/types'

export const useOffersStore = defineStore('offers', () => {
  const offers = ref<OfferSummary[]>([])
  const total = ref(0)
  const campaignFilter = ref<CampaignFilter | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(
    params: { q?: string; remote?: string; limit?: number; campaign?: boolean } = {},
  ): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const search = new URLSearchParams()
      search.set('limit', String(params.limit ?? 100))
      if (params.q) search.set('q', params.q)
      if (params.remote) search.set('remote', params.remote)
      if (params.campaign) search.set('campaign', '1')
      const payload = await apiGet<{
        offers: OfferSummary[]
        total: number
        campaign_filter: CampaignFilter
      }>(`/offers?${search.toString()}`)
      offers.value = payload.offers
      total.value = payload.total
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

  return { offers, total, campaignFilter, loading, error, load, getDetail }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
