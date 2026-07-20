import { fetchApi } from '@/lib/api/client'

export interface ApiKey {
  id: string
  name: string
  masked_value: string
  last_modified: string
}

export interface ApiKeysResponse {
  keys: ApiKey[]
}

export interface AddApiKeyPayload {
  name: string
  value: string
}

export interface AddApiKeyResponse {
  id: string
  name: string
  masked_value: string
  last_modified: string
}

export function fetchApiKeys(): Promise<ApiKeysResponse> {
  return fetchApi<ApiKeysResponse>('/settings/api-keys')
}

export function addApiKey(payload: AddApiKeyPayload): Promise<AddApiKeyResponse> {
  return fetchApi<AddApiKeyResponse>('/settings/api-keys', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteApiKey(id: string): Promise<void> {
  return fetchApi<void>(`/settings/api-keys/${id}`, { method: 'DELETE' })
}
