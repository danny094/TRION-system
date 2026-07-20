import type { ChatEvent } from '@/lib/contracts/chatEvents'

export type SessionId = string

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  events: ChatEvent[]
}

export interface ChatSession {
  id: SessionId
  conversationId: string
  title: string
  messages: Message[]
  isBusy: boolean
  createdAt: string
  updatedAt: string
}
