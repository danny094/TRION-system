/**
 * Basis-API-Client für die WebUI
 * Alle API-Calls laufen im Development-Server über den Vite-Proxy (/api -> 8200).
 */

const API_BASE = '/api'

export class ApiError extends Error {
  public status: number
  public statusText: string
  public body: any
  constructor(status: number, statusText: string, body: any) {
    super(`API Error: ${status} ${statusText}`)
    this.status = status
    this.statusText = statusText
    this.body = body
  }
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
  
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(url, { ...options, headers })

  if (!response.ok) {
    let errorBody = {}
    try {
      errorBody = await response.json()
    } catch {
      errorBody = { text: await response.text() }
    }
    throw new ApiError(response.status, response.statusText, errorBody)
  }

  if (response.status === 204) return null as any
  
  return response.json()
}
