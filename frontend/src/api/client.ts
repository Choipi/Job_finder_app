const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

const DEFAULT_TIMEOUT_MS = 8000

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Minimal typed wrapper around fetch.
 *
 * - The API key never transits through this layer: Flask holds it and only
 *   returns booleans describing the configuration.
 * - Every request gets a timeout so a dead backend cannot freeze the UI.
 */
export async function apiGet<T>(path: string): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })

    const payload = (await response.json().catch(() => null)) as unknown

    if (!response.ok) {
      throw new ApiError(readErrorMessage(payload) ?? `Erreur HTTP ${response.status}`, response.status)
    }

    return payload as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('Le backend Flask ne répond pas (délai dépassé).', 0)
    }
    throw new ApiError('Impossible de joindre le backend Flask.', 0)
  } finally {
    window.clearTimeout(timeout)
  }
}

function readErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') {
    return null
  }
  const maybeError = (payload as { error?: unknown }).error
  if (maybeError && typeof maybeError === 'object') {
    const message = (maybeError as { message?: unknown }).message
    if (typeof message === 'string') {
      return message
    }
  }
  return null
}
