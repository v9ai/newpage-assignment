/**
 * Session CRUD client (POST/GET /api/sessions, GET /api/sessions/{id}).
 * Mirrors api/app/sessions.py. Mock-backed when VITE_USE_MOCKS=true so the chat
 * UI's session switcher and reload-restores-history flows work offline.
 */
import { ApiError } from '../lib/types'
import type { Citation, SessionDetail, SessionSummary } from './types'

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

// ── Mock store ──────────────────────────────────────────────────────────────

type MockSession = SessionDetail
let mockSeq = 1
const mockSessions = new Map<number, MockSession>()

function mockSeed() {
  if (mockSessions.size > 0) return
  const id = mockSeq++
  mockSessions.set(id, {
    id,
    title: 'Welcome chat',
    created_at: new Date().toISOString(),
    messages: [],
  })
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

// ── API ──────────────────────────────────────────────────────────────────────

async function createSession(title?: string): Promise<SessionSummary> {
  if (USE_MOCKS) {
    await delay(120)
    const id = mockSeq++
    const session: MockSession = {
      id,
      title: title ?? 'New chat',
      created_at: new Date().toISOString(),
      messages: [],
    }
    mockSessions.set(id, session)
    return { id, title: session.title, created_at: session.created_at }
  }
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new ApiError(res.status, `Could not create session (${res.status})`)
  return (await res.json()) as SessionSummary
}

async function listSessions(): Promise<SessionSummary[]> {
  if (USE_MOCKS) {
    mockSeed()
    await delay(100)
    return [...mockSessions.values()]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(({ id, title, created_at }) => ({ id, title, created_at }))
  }
  const res = await fetch('/api/sessions')
  if (!res.ok) throw new ApiError(res.status, `Could not load sessions (${res.status})`)
  return (await res.json()) as SessionSummary[]
}

async function getSession(id: number): Promise<SessionDetail> {
  if (USE_MOCKS) {
    mockSeed()
    await delay(100)
    const s = mockSessions.get(id)
    if (!s) throw new ApiError(404, 'Session not found.')
    return structuredClone(s)
  }
  const res = await fetch(`/api/sessions/${id}`)
  if (!res.ok) throw new ApiError(res.status, `Could not load session (${res.status})`)
  return (await res.json()) as SessionDetail
}

/**
 * Record a completed turn into the mock store so a mock reload restores it.
 * No-op against the real API (the server persists on its own).
 */
function mockRecordTurn(
  sessionId: number,
  userContent: string,
  assistantContent: string,
  citations: Citation[],
): void {
  if (!USE_MOCKS) return
  const s = mockSessions.get(sessionId)
  if (!s) return
  const now = Date.now()
  s.messages.push({
    id: now,
    role: 'user',
    content: userContent,
    citations: [],
    created_at: new Date(now).toISOString(),
  })
  s.messages.push({
    id: now + 1,
    role: 'assistant',
    content: assistantContent,
    citations,
    created_at: new Date(now + 1).toISOString(),
  })
  if (s.title === 'New chat' && userContent.trim()) {
    s.title = userContent.trim().slice(0, 40)
  }
}

export const sessionsApi = {
  createSession,
  listSessions,
  getSession,
  mockRecordTurn,
  usingMocks: USE_MOCKS,
}
