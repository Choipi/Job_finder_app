import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiGet, apiPost } from '@/api/client'
import type { ScanResponse, ScanRun, SchedulerStatus } from '@/api/types'

export const useScansStore = defineStore('scans', () => {
  const scanning = ref(false)
  const lastScan = ref<ScanRun | null>(null)
  const scheduler = ref<SchedulerStatus | null>(null)
  const error = ref<string | null>(null)

  async function loadScheduler(): Promise<void> {
    try {
      scheduler.value = await apiGet<SchedulerStatus>('/scheduler')
    } catch (cause) {
      error.value = messageOf(cause)
    }
  }

  async function runScan(payload: {
    collect_limit: number
    max_offers: number
    score_limit: number
  }): Promise<ScanResponse> {
    scanning.value = true
    error.value = null
    try {
      const response = await apiPost<ScanResponse>('/scan', payload, 360_000)
      lastScan.value = response.scan
      return response
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      scanning.value = false
    }
  }

  return { scanning, lastScan, scheduler, error, loadScheduler, runScan }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
