import type {
  ConversationPolicy,
  ConversationSummary,
  DeleteResponse,
  MemoryEntry,
  SearchRequest,
  SearchResponse,
} from './contracts'
import { fetchApi } from '@/lib/api/client'

export async function fetchRecent(conversationId?: string | null, limit = 20): Promise<MemoryEntry[]> {
  const params = new URLSearchParams()
  if (conversationId) params.set('conversation_id', conversationId)
  params.set('limit', String(limit))
  const payload = await fetchApi<{ entries: MemoryEntry[]; count: number }>(`/memory/recent?${params.toString()}`)
  return payload.entries ?? []
}

export async function fetchConversations(limit = 50): Promise<ConversationSummary[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  const payload = await fetchApi<{ conversations: ConversationSummary[]; count: number }>(`/memory/conversations?${params.toString()}`)
  return payload.conversations ?? []
}

export async function fetchConversationEntries(conversationId: string, limit = 50): Promise<MemoryEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  const payload = await fetchApi<{ entries: MemoryEntry[]; count: number }>(`/memory/conversations/${encodeURIComponent(conversationId)}?${params.toString()}`)
  return payload.entries ?? []
}

export async function fetchConversationPolicy(conversationId: string): Promise<ConversationPolicy> {
  return fetchApi<ConversationPolicy>(`/memory/conversations/${encodeURIComponent(conversationId)}/policy`)
}

export async function searchMemory(request: SearchRequest): Promise<SearchResponse> {
  return fetchApi<SearchResponse>('/memory/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export async function deleteMemory(id: number): Promise<DeleteResponse> {
  return fetchApi<DeleteResponse>(`/memory/${id}`, { method: 'DELETE' })
}

export async function deleteMemoryBulk(ids: number[]): Promise<DeleteResponse> {
  return fetchApi<DeleteResponse>('/memory/delete-bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
}
