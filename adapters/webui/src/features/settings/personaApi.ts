import { fetchApi } from '@/lib/api/client'

export interface PersonaListResponse {
  personas: string[]
  active: string
  count: number
}

export interface PersonaDetailResponse {
  name: string
  content: string
  exists: boolean
  size: number
  active: boolean
}

export interface PersonaSaveResponse {
  success: boolean
  name: string
  active: boolean
  size: number
}

export function fetchPersonas(): Promise<PersonaListResponse> {
  return fetchApi<PersonaListResponse>('/personas/')
}

export function fetchPersona(name: string): Promise<PersonaDetailResponse> {
  return fetchApi<PersonaDetailResponse>(`/personas/${encodeURIComponent(name)}`)
}

export function updatePersona(name: string, content: string): Promise<PersonaSaveResponse> {
  return fetchApi<PersonaSaveResponse>(`/personas/content/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
}

export function switchPersona(name: string): Promise<{ success: boolean; current: string }> {
  return fetchApi<{ success: boolean; current: string }>(`/personas/switch?name=${encodeURIComponent(name)}`, {
    method: 'PUT',
  })
}
