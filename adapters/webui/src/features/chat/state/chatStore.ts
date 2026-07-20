import { create } from 'zustand'
import type { ChatEvent, TaskLoopStateEvent } from '@/lib/contracts/chatEvents'
import { approveTask, sendMessageStream } from '../api'
import type { ChatMessage } from '../api'
import { createChatSession, createMessageId, deriveSessionTitleFromMessage } from '../lib/sessionFactory'
import { findSessionIndex, getActiveSession } from '../lib/sessionSelectors'
import type { ChatSession, SessionId } from '../types'

interface ChatState {
  sessions: ChatSession[]
  activeSessionId: SessionId | null
  createSession: () => SessionId
  activateSession: (sessionId: SessionId) => void
  closeSession: (sessionId: SessionId) => void
  sendMessage: (content: string) => Promise<void>
  approveWaitingTask: (sessionId: SessionId, messageId: string, taskId: string) => Promise<void>
}

function getErrorContent(event: ChatEvent): string {
  if (event.type !== 'error') return ''
  const value = 'content' in event ? event.content : ''
  return typeof value === 'string' ? value : ''
}

function getEventContent(event: ChatEvent): string {
  const value = 'content' in event ? event.content : ''
  return typeof value === 'string' ? value : ''
}

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
  sendMessage: async (content: string) => {
    const activeSession = getActiveSession(get().sessions, get().activeSessionId)
    if (!activeSession) return

    const sessionId = activeSession.id
    const userMsgId = createMessageId('usr')
    const asstMsgId = createMessageId('ast')
    const timestamp = new Date().toISOString()

    set((state) => ({
      sessions: state.sessions.map((session) => {
        if (session.id !== sessionId) return session
        const title = session.messages.length === 0
          ? deriveSessionTitleFromMessage(content, session.title)
          : session.title
        return {
          ...session,
          isBusy: true,
          title,
          updatedAt: timestamp,
          messages: [
            ...session.messages,
            { id: userMsgId, role: 'user', content, events: [] },
            { id: asstMsgId, role: 'assistant', content: '', isStreaming: true, events: [] },
          ],
        }
      }),
    }))

    const historySession = getActiveSession(get().sessions, sessionId)
    if (!historySession) return

    const history: ChatMessage[] = historySession.messages
      .filter(m => m.id !== asstMsgId && m.id !== userMsgId)
      .map(m => ({ role: m.role, content: m.content }))
    const messages: ChatMessage[] = [...history, { role: 'user', content }]

    try {
      const stream = await sendMessageStream(messages, historySession.conversationId)

      for await (const event of stream) {
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id !== sessionId) return session
            const messages = [...session.messages]
            const asstMsg = messages.find((message) => message.id === asstMsgId)
            if (!asstMsg) return session

            asstMsg.events.push(event)

            if (event.type === 'content') {
              asstMsg.content += getEventContent(event)
            } else if (event.type === 'final_content') {
              asstMsg.content = getEventContent(event)
            } else if (event.type === 'error') {
              const errContent = getErrorContent(event)
              if (errContent) asstMsg.content += `\n\n**Fehler:** ${errContent}`
            } else if (event.type === 'done') {
              asstMsg.isStreaming = false
            }

            return {
              ...session,
              messages,
              updatedAt: new Date().toISOString(),
            }
          })

          return { sessions }
        })
      }
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : 'Unbekannter Fehler'
      set((state) => {
        const sessions = state.sessions.map((session) => {
          if (session.id !== sessionId) return session
          const messages = [...session.messages]
          const asstMsg = messages.find((message) => message.id === asstMsgId)
          if (asstMsg) {
            asstMsg.isStreaming = false
            asstMsg.content = asstMsg.content || `**Verbindungsfehler:** ${errMsg}`
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
      return
    }

    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? { ...session, isBusy: false, updatedAt: new Date().toISOString() }
          : session,
      ),
    }))
  },
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
