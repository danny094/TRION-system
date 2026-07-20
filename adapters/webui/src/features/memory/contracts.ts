/**
 * Memory-App Contracts.
 *
 * Diese Typen sind die WebUI-Sicht auf das Memory-System. Sie spiegeln nicht
 * direkt die MCP-Tool-Schemas wider — die Admin-API ueberbrueckt das (siehe
 * docs/memory-grounding/34-semantic-tool-truth-drift.md: Tool-Existenz nicht spiegeln, sondern
 * dedizierte Contracts ausstellen).
 */

export type MemoryLayer = 'stm' | 'mtm' | 'ltm' | 'auto'

export interface MemoryEntry {
  id: number
  conversation_id: string
  role?: string
  content: string
  tags?: string
  layer?: MemoryLayer
  created_at: string
}

export interface ConversationSummary {
  conversation_id: string
  title?: string
  last_activity_at?: string
  entry_count?: number
}

export type MemoryMode = 'global_enabled' | 'conversation_only' | 'disabled'

export interface ConversationPolicy {
  memory_mode: MemoryMode
  allow_global_memory_read: boolean
  allow_long_term_write: boolean
  do_not_remember: boolean
  temporary: boolean
  badge: PolicyBadge
}

export type PolicyBadge =
  | 'global_enabled'
  | 'conversation_only'
  | 'temporary'
  | 'do_not_remember'
  | 'disabled'

export type SearchMode = 'fts' | 'semantic' | 'graph'

export interface SearchRequest {
  query: string
  mode: SearchMode
  conversation_id?: string
  limit?: number
}

export interface SearchHit {
  id?: number
  conversation_id?: string
  content: string
  score?: number
  layer?: MemoryLayer
  created_at?: string
  source: SearchMode
}

export interface SearchResponse {
  mode: SearchMode
  query: string
  hits: SearchHit[]
  count: number
}

export interface DeleteBulkRequest {
  ids: number[]
}

export interface DeleteResponse {
  ok: boolean
  deleted_count: number
  error?: string
}
