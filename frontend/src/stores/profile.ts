import { ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, apiDelete, apiGet, apiPostForm, apiPut } from '@/api/client'
import type { Profile, ProfilePayload } from '@/api/types'

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<Profile | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)

  async function load(): Promise<Profile> {
    loading.value = true
    error.value = null
    try {
      const payload = await apiGet<{ profile: Profile }>('/profile')
      profile.value = payload.profile
      return payload.profile
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function save(values: ProfilePayload): Promise<Profile> {
    saving.value = true
    error.value = null
    try {
      const payload = await apiPut<{ profile: Profile }>('/profile', values)
      profile.value = payload.profile
      return payload.profile
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      saving.value = false
    }
  }

  async function uploadCv(file: File): Promise<Profile> {
    uploading.value = true
    error.value = null
    try {
      const form = new FormData()
      form.append('file', file)
      const payload = await apiPostForm<{ profile: Profile }>('/profile/cv', form)
      profile.value = payload.profile
      return payload.profile
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      uploading.value = false
    }
  }

  async function removeCv(): Promise<Profile> {
    saving.value = true
    error.value = null
    try {
      const payload = await apiDelete<{ profile: Profile }>('/profile/cv')
      profile.value = payload.profile
      return payload.profile
    } catch (cause) {
      error.value = messageOf(cause)
      throw cause
    } finally {
      saving.value = false
    }
  }

  return { profile, loading, saving, uploading, error, load, save, uploadCv, removeCv }
})

export function messageOf(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'Une erreur inattendue est survenue.'
}
