import { parseNDJSONStream } from '@/lib/stream/ndjsonParser'
import type { ChatEvent } from '@/lib/contracts/chatEvents'
import { fetchApi, fetchApiResponse } from '@/lib/api/client'

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
  const response = await fetchApiResponse('/chat', {
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
  return fetchApi<TaskApproveResponse>(`/tasks/${encodeURIComponent(taskId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_text: userText }),
  })

}
