import type { StoreApi } from 'zustand'
import type { ChatEvent } from '@/lib/contracts/chatEvents'
import { sendMessageStream } from '../api'
import type { ChatMessage } from '../api'
import { createMessageId, deriveSessionTitleFromMessage } from '../lib/sessionFactory'
import { getActiveSession } from '../lib/sessionSelectors'
import type { ChatState } from '../types'
import { translateCurrent } from '@/lib/i18n'

type SetChatState = StoreApi<ChatState>['setState']
type GetChatState = StoreApi<ChatState>['getState']

function getErrorContent(event: ChatEvent): string {
  if (event.type !== 'error') return ''
  const value = 'content' in event ? event.content : ''
  return typeof value === 'string' ? value : ''
}

function getEventContent(event: ChatEvent): string {
  const value = 'content' in event ? event.content : ''
  return typeof value === 'string' ? value : ''
}

export function createSendMessageAction(
  set: SetChatState,
  get: GetChatState,
): ChatState['sendMessage'] {
  return async (content: string) => {
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
              if (errContent) asstMsg.content += `\n\n**${translateCurrent('chat.error')}:** ${errContent}`
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
      const errMsg = error instanceof Error ? error.message : translateCurrent('chat.unknownError')
      set((state) => {
        const sessions = state.sessions.map((session) => {
          if (session.id !== sessionId) return session
          const messages = [...session.messages]
          const asstMsg = messages.find((message) => message.id === asstMsgId)
          if (asstMsg) {
            asstMsg.isStreaming = false
            asstMsg.content = asstMsg.content || `**${translateCurrent('chat.connectionError')}:** ${errMsg}`
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
  }
}
