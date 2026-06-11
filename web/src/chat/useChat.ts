import { useCallback, useEffect, useRef, useState } from 'react'
import { sessionsApi } from './sessions-api'
import { streamMessage } from './sse'
import type { StreamHandle } from './sse'
import type { Citation, ChatMessage, SessionSummary } from './types'

let localId = 0
const nextLocalId = () => `local-${++localId}`

interface UseChat {
  sessions: SessionSummary[]
  activeId: number | null
  messages: ChatMessage[]
  streaming: boolean
  sessionsError: string | null
  selectSession: (id: number) => void
  newSession: () => Promise<void>
  send: (content: string) => Promise<void>
}

/**
 * Owns chat state: the session list, the active session's messages, and the
 * live SSE stream for the in-flight assistant turn. Reloading restores prior
 * sessions and messages from the API (done-when), since nothing is kept only
 * in memory.
 */
export function useChat(): UseChat {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [sessionsError, setSessionsError] = useState<string | null>(null)
  const stream = useRef<StreamHandle | null>(null)

  // Load sessions once on mount.
  useEffect(() => {
    let cancelled = false
    sessionsApi
      .listSessions()
      .then((list) => {
        if (cancelled) return
        setSessions(list)
        setSessionsError(null)
        if (list.length > 0) setActiveId((cur) => cur ?? list[0].id)
      })
      .catch((e) => {
        if (cancelled) return
        setSessionsError(e instanceof Error ? e.message : 'Could not load sessions.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Load the active session's messages whenever it changes. (When activeId is
  // null there is nothing to load; messages are cleared by the callbacks that
  // set it null, so the effect simply no-ops.)
  useEffect(() => {
    if (activeId == null) return
    let cancelled = false
    sessionsApi
      .getSession(activeId)
      .then((detail) => {
        if (cancelled) return
        setMessages(
          detail.messages.map((m) => ({
            id: String(m.id),
            role: m.role,
            content: m.content,
            citations: m.citations ?? [],
          })),
        )
      })
      .catch(() => {
        if (!cancelled) setMessages([])
      })
    return () => {
      cancelled = true
    }
  }, [activeId])

  // Abort any in-flight stream on unmount.
  useEffect(() => () => stream.current?.cancel(), [])

  const selectSession = useCallback((id: number) => {
    stream.current?.cancel()
    setStreaming(false)
    setActiveId(id)
  }, [])

  const newSession = useCallback(async () => {
    const created = await sessionsApi.createSession()
    setSessions((prev) => [created, ...prev])
    setActiveId(created.id)
    setMessages([])
  }, [])

  const send = useCallback(
    async (content: string) => {
      const text = content.trim()
      if (!text || streaming) return

      // Ensure a session exists.
      let sessionId = activeId
      if (sessionId == null) {
        const created = await sessionsApi.createSession()
        setSessions((prev) => [created, ...prev])
        setActiveId(created.id)
        sessionId = created.id
      }

      const userMsg: ChatMessage = {
        id: nextLocalId(),
        role: 'user',
        content: text,
        citations: [],
      }
      const assistantId = nextLocalId()
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        citations: [],
        streaming: true,
      }
      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setStreaming(true)

      let collected = ''
      let citations: Citation[] = []

      const patch = (fn: (m: ChatMessage) => ChatMessage) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)))

      const finish = () => {
        setStreaming(false)
        stream.current = null
        // Give the freshly created session a title from the first question.
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId && (s.title === 'New chat' || !s.title)
              ? { ...s, title: text.slice(0, 40) }
              : s,
          ),
        )
      }

      stream.current = streamMessage(sessionId, text, (e) => {
        switch (e.type) {
          case 'token':
            collected += e.delta
            patch((m) => ({ ...m, content: collected }))
            break
          case 'citations':
            citations = e.citations
            patch((m) => ({ ...m, citations }))
            break
          case 'error':
            patch((m) => ({
              ...m,
              streaming: false,
              errored: true,
              content: collected || e.message,
            }))
            finish()
            break
          case 'done':
            patch((m) => ({
              ...m,
              streaming: false,
              content: collected,
              citations,
              id: e.message_id || m.id,
            }))
            sessionsApi.mockRecordTurn(sessionId!, text, collected, citations)
            finish()
            break
        }
      })
    },
    [activeId, streaming],
  )

  return {
    sessions,
    activeId,
    messages,
    streaming,
    sessionsError,
    selectSession,
    newSession,
    send,
  }
}
