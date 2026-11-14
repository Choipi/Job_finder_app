const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

const DEFAULT_TIMEOUT_MS = 15_000
const UPLOAD_TIMEOUT_MS = 45_000

export class ApiError extends Error {
  readonly status: number
  readonly fields: Record<string, string>

  constructor(message: string, status: number, fields: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  json?: unknown
  form?: FormData
  timeoutMs?: number
}

/**
 * Minimal typed wrapper around fetch.
 *
 * - The API key never transits through this layer: Flask holds it and only
 *   returns booleans describing the configuration.
 * - Every request gets a timeout so a dead backend cannot freeze the UI.
 * - Validation errors carry a `fields` map used by the forms.
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  )

  const headers: Record<string, string> = { Accept: 'application/json' }
  let body: BodyInit | undefined

  if (options.form) {
    body = options.form
  } else if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body,
      signal: controller.signal,
    })

    if (response.status === 204) {
      return undefined as T
    }

    const payload = (await response.json().catch(() => null)) as unknown

    if (!response.ok) {
      throw new ApiError(
        readErrorMessage(payload) ?? `Erreur HTTP ${response.status}`,
        response.status,
        readErrorFields(payload),
      )
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

export const apiGet = <T>(path: string): Promise<T> => request<T>(path)

export const apiPut = <T>(path: string, json: unknown): Promise<T> =>
  request<T>(path, { method: 'PUT', json })

export const apiPostForm = <T>(path: string, form: FormData): Promise<T> =>
  request<T>(path, { method: 'POST', form, timeoutMs: UPLOAD_TIMEOUT_MS })

export const apiDelete = <T>(path: string): Promise<T> =>
  request<T>(path, { method: 'DELETE' })

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

function readErrorFields(payload: unknown): Record<string, string> {
  if (!payload || typeof payload !== 'object') {
    return {}
  }
  const maybeError = (payload as { error?: unknown }).error
  if (!maybeError || typeof maybeError !== 'object') {
    return {}
  }
  const fields = (maybeError as { fields?: unknown }).fields
  if (!fields || typeof fields !== 'object') {
    return {}
  }

  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(fields)) {
    if (typeof value === 'string') {
      result[key] = value
    }
  }
  return result
}
