import { fetchApi } from '@/lib/api/client'

export type MemoryMode = 'global_enabled' | 'conversation_only' | 'disabled'

export interface MemoryDefaults {
  memory_mode: MemoryMode
  do_not_remember: boolean
  max_memory_hits: number
}

export interface MemoryDerived {
  allow_global_memory_read: boolean
  allow_long_term_write: boolean
}

export interface MemoryDefaultsResponse {
  defaults: MemoryDefaults
  derived: MemoryDerived
  fallback: MemoryDefaults
  sources: Record<string, string>
}

export type MemoryDefaultsUpdate = Partial<MemoryDefaults>

export interface MemoryDefaultsSaveResponse {
  success: boolean
  saved: MemoryDefaultsUpdate
  defaults: MemoryDefaults
  derived: MemoryDerived
}

export function fetchMemoryDefaults(): Promise<MemoryDefaultsResponse> {
  return fetchApi<MemoryDefaultsResponse>('/settings/memory/defaults')
}

export function updateMemoryDefaults(
  payload: MemoryDefaultsUpdate,
): Promise<MemoryDefaultsSaveResponse> {
  return fetchApi<MemoryDefaultsSaveResponse>('/settings/memory/defaults', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
