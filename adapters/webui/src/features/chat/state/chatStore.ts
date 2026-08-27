import { create } from 'zustand'
import type { TaskLoopStateEvent } from '@/lib/contracts/chatEvents'
import { approveTask } from '../api'
import { createChatSession } from '../lib/sessionFactory'
import { findSessionIndex } from '../lib/sessionSelectors'
import type { ChatState, SessionId } from '../types'
import { createSendMessageAction } from './chatMessageStreaming'

const initialSession = createChatSession(1)

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [initialSession],
  activeSessionId: initialSession.id,
  createSession: () => {
    const nextSession = createChatSession(get().sessions.length + 1)
    set((state) => ({
      sessions: [nextSession, ...state.sessions],
      activeSessionId: nextSession.id,
    }))
    return nextSession.id
  },
  activateSession: (sessionId: SessionId) => {
    set((state) => {
      if (findSessionIndex(state.sessions, sessionId) < 0) return state
      return { activeSessionId: sessionId }
    })
  },
  closeSession: (sessionId: SessionId) => {
    set((state) => {
      if (state.sessions.length <= 1) return state
      const closingIndex = findSessionIndex(state.sessions, sessionId)
      if (closingIndex < 0) return state

      const sessions = state.sessions.filter((session) => session.id !== sessionId)
      const activeSessionId = state.activeSessionId === sessionId
        ? sessions[Math.max(0, closingIndex - 1)]?.id ?? sessions[0]?.id ?? null
        : state.activeSessionId

      return { sessions, activeSessionId }
    })
  },
  sendMessage: createSendMessageAction(set, get),
  approveWaitingTask: async (sessionId: SessionId, messageId: string, taskId: string) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? { ...session, isBusy: true, updatedAt: new Date().toISOString() }
          : session,
      ),
    }))

    try {
      const result = await approveTask(taskId)
      set((state) => {
        const sessions = state.sessions.map((session) => {
          if (session.id !== sessionId) return session

          const messages = [...session.messages]
          const message = messages.find((entry) => entry.id === messageId)
          if (!message) {
            return { ...session, isBusy: false }
          }

          const snapshot = result.snapshot ?? {}
          const nextStateEvent: TaskLoopStateEvent = {
            type: 'task_loop_state',
            model: 'task-resume',
            conversation_id: String(snapshot.conversation_id ?? session.conversationId),
            created_at: new Date().toISOString(),
            done: false,
            state: result.state as TaskLoopStateEvent['state'],
            step_index: Number(snapshot.current_step_index ?? 0),
            total_steps: Number(snapshot.total_steps ?? 0),
            stop_reason: (result.stop_reason ?? null) as TaskLoopStateEvent['stop_reason'],
            completed_count: Number(snapshot.completed_count ?? 0),
            artifact_count: Array.isArray(result.artifacts) ? result.artifacts.length : 0,
          }

          message.events.push(nextStateEvent)
          if (result.visible_content) {
            message.content = [message.content, result.visible_content].filter(Boolean).join('\n\n')
          }
          message.isStreaming = false

          return {
            ...session,
            isBusy: false,
            messages,
            updatedAt: new Date().toISOString(),
          }
        })

        return { sessions }
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Task approval failed'
      set((state) => {
        const sessions = state.sessions.map((session) => {
          if (session.id !== sessionId) return session

          const messages = [...session.messages]
          const message = messages.find((entry) => entry.id === messageId)
          if (message) {
            message.content = [message.content, `**Approval-Fehler:** ${errorMessage}`].filter(Boolean).join('\n\n')
            message.isStreaming = false
          }

          return {
            ...session,
            isBusy: false,
            messages,
            updatedAt: new Date().toISOString(),
          }
        })
        return { sessions }
      })
    }
  },
}))
