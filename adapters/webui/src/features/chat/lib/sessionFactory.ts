import type { ChatSession } from '../types'

function uniqueToken(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export function createConversationId(): string {
  return uniqueToken('conv')
}

export function createSessionTitle(index: number): string {
  return index <= 1 ? 'Neuer Chat' : `Neuer Chat ${index}`
}

export function createChatSession(index: number): ChatSession {
  const createdAt = new Date().toISOString()
  return {
    id: uniqueToken('session'),
    conversationId: createConversationId(),
    title: createSessionTitle(index),
    messages: [],
    isBusy: false,
    createdAt,
    updatedAt: createdAt,
  }
}

export function createMessageId(prefix: 'usr' | 'ast'): string {
  return uniqueToken(prefix)
}

export function deriveSessionTitleFromMessage(content: string, fallback: string): string {
  const trimmed = content.trim()
  if (!trimmed) return fallback
  const compact = trimmed.replace(/\s+/g, ' ')
  return compact.length <= 32 ? compact : `${compact.slice(0, 32).trimEnd()}…`
}
