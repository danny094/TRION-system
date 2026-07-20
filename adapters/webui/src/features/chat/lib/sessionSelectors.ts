import type { ChatSession, SessionId } from '../types'

export function findSessionIndex(sessions: ChatSession[], sessionId: SessionId | null): number {
  if (!sessionId) return -1
  return sessions.findIndex((session) => session.id === sessionId)
}

export function getActiveSession(
  sessions: ChatSession[],
  activeSessionId: SessionId | null,
): ChatSession | null {
  const index = findSessionIndex(sessions, activeSessionId)
  return index >= 0 ? sessions[index] ?? null : null
}
