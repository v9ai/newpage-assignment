/**
 * Chat types mirroring the live contract (api/app/chat.py + sessions.py):
 *   SSE events: token {delta} · citations {citations} · error {message}
 *               · done {message_id, usage}
 *   Citation:   { doc_id, filename, page, chunk_index, snippet }
 * A refusal is a normal token-streamed answer distinguished by citations: [].
 */

export interface Citation {
  doc_id: string
  filename: string
  page: number | null
  chunk_index: number
  snippet: string
}

export type Role = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: Role
  content: string
  citations: Citation[]
  /** True while assistant tokens are still streaming in. */
  streaming?: boolean
  /** True if this assistant turn errored mid-stream. */
  errored?: boolean
}

export interface SessionSummary {
  id: number
  title: string
  created_at: string
}

export interface SessionDetail extends SessionSummary {
  messages: {
    id: number
    role: Role
    content: string
    citations: Citation[]
    created_at: string
  }[]
}

/** Discriminated union of decoded SSE events. */
export type ChatEvent =
  | { type: 'token'; delta: string }
  | { type: 'citations'; citations: Citation[] }
  | { type: 'error'; message: string }
  | { type: 'done'; message_id: string; usage: Record<string, unknown> }
