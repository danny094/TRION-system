import { parseNDJSONStream } from '@/lib/stream/ndjsonParser'
import type { ChatEvent } from '@/lib/contracts/chatEvents'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export async function sendMessageStream(
  messages: ChatMessage[],
  conversationId: string,
  model: string = 'default',
  autonomousMode: boolean = false
): Promise<AsyncGenerator<ChatEvent, void, unknown>> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      model,
      conversation_id: conversationId,
      stream: true,
      autonomous_mode: autonomousMode,
    })
  })

  if (!response.ok) {
    throw new Error(`Chat API failed: ${response.status} ${response.statusText}`)
  }

  return parseNDJSONStream(response)
}

export interface TaskApproveResponse {
  state: string
  stop_reason: string | null
  visible_content: string
  artifacts: Array<Record<string, unknown>>
  snapshot: Record<string, unknown>
}

export async function approveTask(
  taskId: string,
  userText: string = 'approve'
): Promise<TaskApproveResponse> {
  const response = await fetch(`/api/tasks/${encodeURIComponent(taskId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_text: userText }),
  })

  if (!response.ok) {
    throw new Error(`Task approve failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<TaskApproveResponse>
}
