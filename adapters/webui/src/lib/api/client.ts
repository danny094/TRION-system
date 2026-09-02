/** Central same-origin security boundary for WebUI API calls. */
const API_BASE = '/api'
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
export const SESSION_LOST_EVENT = 'trion:session-lost'
let csrfToken: string | null = null

export interface ApiErrorBody {
  detail?: unknown
  text?: string
  value?: unknown
  [key: string]: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly statusText: string
  readonly body: ApiErrorBody

  constructor(status: number, statusText: string, body: ApiErrorBody) {
    super(`API Error: ${status} ${statusText}`)
    this.status = status
    this.statusText = statusText
    this.body = body
  }
}

export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

function securedOptions(options: RequestInit): RequestInit {
  const method = String(options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (MUTATING_METHODS.has(method) && csrfToken) {
    headers.set('x-csrf-token', csrfToken)
  }
  return { ...options, method, headers, credentials: 'same-origin' }
}

export async function fetchApiResponse(
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> {
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const response = await fetch(`${API_BASE}${path}`, securedOptions(options))
  if (response.status === 401) {
    setCsrfToken(null)
    window.dispatchEvent(new CustomEvent(SESSION_LOST_EVENT))
  }
  if (!response.ok) {
    let body: ApiErrorBody
    try {
      const parsed: unknown = await response.clone().json()
      body = parsed && typeof parsed === 'object' ? parsed as ApiErrorBody : { value: parsed }
    } catch {
      body = { text: await response.text() }
    }
    throw new ApiError(response.status, response.statusText, body)
  }
  return response
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetchApiResponse(endpoint, options)
  if (response.status === 204) return null as T
  return response.json() as Promise<T>
}
