import type { ChatEvent } from '@/lib/contracts/chatEvents'

export async function* parseNDJSONStream(response: Response): AsyncGenerator<ChatEvent, void, unknown> {
  if (!response.body) {
    throw new Error("No response body available for streaming")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const event = JSON.parse(line) as ChatEvent
          yield event
        } catch (e) {
          console.error("Failed to parse NDJSON line:", line, e)
        }
      }
    }
    
    if (buffer.trim()) {
      try {
        const event = JSON.parse(buffer) as ChatEvent
        yield event
      } catch (e) {
        console.error("Failed to parse final NDJSON line:", buffer, e)
      }
    }
  } finally {
    reader.releaseLock()
  }
}
