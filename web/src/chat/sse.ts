/**
 * SSE client for the chat endpoint. The endpoint is a POST that returns a
 * text/event-stream (sse-starlette), so the browser's EventSource (GET-only)
 * can't be used — we read the streamed body and parse SSE frames by hand.
 *
 * A scripted mock stream (mockChatStream) emits the same contract events so the
 * UI is fully developed and tested before unit 07's endpoint is wired in.
 * Toggle with VITE_USE_MOCKS=true (shared with the documents mock).
 */
import type { ChatEvent, Citation } from './types'

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

/** Parse one SSE frame ("event: x\ndata: {...}") into a ChatEvent, or null. */
function parseFrame(frame: string): ChatEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (dataLines.length === 0) return null
  let data: unknown
  try {
    data = JSON.parse(dataLines.join('\n'))
  } catch {
    return null
  }
  const d = data as Record<string, unknown>
  switch (event) {
    case 'token':
      return { type: 'token', delta: String(d.delta ?? '') }
    case 'citations':
      return { type: 'citations', citations: (d.citations ?? []) as Citation[] }
    case 'error':
      return { type: 'error', message: String(d.message ?? 'Unknown error') }
    case 'done':
      return {
        type: 'done',
        message_id: String(d.message_id ?? ''),
        usage: (d.usage ?? {}) as Record<string, unknown>,
      }
    default:
      return null
  }
}

export interface StreamHandle {
  cancel: () => void
}

/**
 * POST a user message to a session and invoke `onEvent` for each decoded SSE
 * event. Returns a handle whose `cancel()` aborts the in-flight stream.
 */
export function streamMessage(
  sessionId: number,
  content: string,
  onEvent: (e: ChatEvent) => void,
): StreamHandle {
  if (USE_MOCKS) return mockChatStream(content, onEvent)

  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(`/api/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      })
      if (!res.ok || !res.body) {
        let message = `Request failed (${res.status})`
        try {
          const body = (await res.json()) as { detail?: string }
          if (body.detail) message = body.detail
        } catch {
          // keep default
        }
        onEvent({ type: 'error', message })
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // SSE frames are separated by a blank line.
        let sep: number
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, sep)
          buffer = buffer.slice(sep + 2)
          const evt = parseFrame(frame)
          if (evt) onEvent(evt)
        }
      }
    } catch (e) {
      if (controller.signal.aborted) return
      onEvent({
        type: 'error',
        message:
          e instanceof Error ? e.message : 'Connection to the assistant failed.',
      })
    }
  })()

  return { cancel: () => controller.abort() }
}

// ── Scripted mock stream ────────────────────────────────────────────────────

const SAMPLE_CITATIONS: Citation[] = [
  {
    doc_id: '1',
    filename: 'q3-earnings-report.pdf',
    page: 4,
    chunk_index: 2,
    snippet:
      'Total revenue for Q3 reached $48.2M, up 23% year over year, driven by ' +
      'expansion in the enterprise segment and stronger net retention.',
  },
  {
    doc_id: '2',
    filename: 'product-spec.md',
    page: null,
    chunk_index: 0,
    snippet:
      'The ingestion pipeline chunks documents at 512 tokens with 64-token ' +
      'overlap before embedding with bge-small-en-v1.5.',
  },
]

function mockChatStream(
  content: string,
  onEvent: (e: ChatEvent) => void,
): StreamHandle {
  let cancelled = false
  const timers: number[] = []
  const at = (ms: number, fn: () => void) => {
    timers.push(window.setTimeout(() => !cancelled && fn(), ms))
  }

  const lower = content.toLowerCase()
  // Three scripted branches so every state is demoable without a backend.
  const branch = /\berror\b|\bfail\b/.test(lower)
    ? 'error'
    : /weather|stock price|unrelated|not in/.test(lower)
      ? 'refusal'
      : 'answer'

  if (branch === 'error') {
    at(400, () => onEvent({ type: 'token', delta: 'Let me check' }))
    at(900, () =>
      onEvent({
        type: 'error',
        message: 'The assistant is temporarily unavailable (rate limited). Please retry.',
      }),
    )
    return { cancel: () => ((cancelled = true), timers.forEach(clearTimeout)) }
  }

  const answer =
    branch === 'refusal'
      ? "I couldn't find anything about that in your documents."
      : 'Based on the Q3 report, revenue grew 23% year over year to $48.2M, with ' +
        'the enterprise segment as the primary driver. The product spec notes the ' +
        'ingestion pipeline uses 512-token chunks with 64-token overlap.'

  const tokens = answer.match(/\S+\s*/g) ?? [answer]
  let t = 350
  for (const tok of tokens) {
    at(t, () => onEvent({ type: 'token', delta: tok }))
    t += 45
  }
  at(t + 200, () =>
    onEvent({
      type: 'citations',
      citations: branch === 'refusal' ? [] : SAMPLE_CITATIONS,
    }),
  )
  at(t + 400, () =>
    onEvent({
      type: 'done',
      message_id: `mock-${Date.now()}`,
      usage: { context_chunks: branch === 'refusal' ? 0 : SAMPLE_CITATIONS.length },
    }),
  )

  return {
    cancel: () => {
      cancelled = true
      timers.forEach(clearTimeout)
    },
  }
}

export const chatUsesMocks = USE_MOCKS
