import type {
  ConversationPolicy,
  ConversationSummary,
  DeleteResponse,
  MemoryEntry,
  SearchRequest,
  SearchResponse,
} from './contracts'

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export async function fetchRecent(conversationId?: string | null, limit = 20): Promise<MemoryEntry[]> {
  const params = new URLSearchParams()
  if (conversationId) params.set('conversation_id', conversationId)
  params.set('limit', String(limit))
  const response = await fetch(`/api/memory/recent?${params.toString()}`)
  const payload = await readJson<{ entries: MemoryEntry[]; count: number }>(response)
  return payload.entries ?? []
}

export async function fetchConversations(limit = 50): Promise<ConversationSummary[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  const response = await fetch(`/api/memory/conversations?${params.toString()}`)
  const payload = await readJson<{ conversations: ConversationSummary[]; count: number }>(response)
  return payload.conversations ?? []
}

export async function fetchConversationEntries(conversationId: string, limit = 50): Promise<MemoryEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  const response = await fetch(`/api/memory/conversations/${encodeURIComponent(conversationId)}?${params.toString()}`)
  const payload = await readJson<{ entries: MemoryEntry[]; count: number }>(response)
  return payload.entries ?? []
}

export async function fetchConversationPolicy(conversationId: string): Promise<ConversationPolicy> {
  const response = await fetch(`/api/memory/conversations/${encodeURIComponent(conversationId)}/policy`)
  return readJson<ConversationPolicy>(response)
}

export async function searchMemory(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch('/api/memory/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  return readJson<SearchResponse>(response)
}

export async function deleteMemory(id: number): Promise<DeleteResponse> {
  const response = await fetch(`/api/memory/${id}`, { method: 'DELETE' })
  return readJson<DeleteResponse>(response)
}

export async function deleteMemoryBulk(ids: number[]): Promise<DeleteResponse> {
  const response = await fetch('/api/memory/delete-bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
  return readJson<DeleteResponse>(response)
}
