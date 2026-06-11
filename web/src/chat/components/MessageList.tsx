import { useEffect, useRef } from 'react'
import type { Citation, ChatMessage } from '../types'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: ChatMessage[]
  hasDocuments: boolean
  onOpenCitation: (c: Citation) => void
}

const SUGGESTIONS = [
  'Summarize the key points across my documents.',
  'What are the main risks mentioned?',
  'What does the report say about revenue?',
]

export function MessageList({ messages, hasDocuments, onOpenCitation }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  // Keep the latest message in view as tokens stream.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-10 text-center">
        <span
          className="grid size-14 place-items-center rounded-2xl bg-accent-soft text-accent"
          aria-hidden="true"
        >
          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </span>
        {hasDocuments ? (
          <>
            <div>
              <p className="font-semibold text-ink">Ask anything about your documents</p>
              <p className="mt-1 text-sm text-ink-muted">
                Answers are grounded in your uploads, with citations to the source.
              </p>
            </div>
            <ul className="flex max-w-sm flex-col gap-1.5 text-sm text-ink-muted">
              {SUGGESTIONS.map((s) => (
                <li
                  key={s}
                  className="rounded-lg bg-surface-sunken px-3 py-2 text-left"
                >
                  {s}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div>
            <p className="font-semibold text-ink">No documents yet</p>
            <p className="mt-1 max-w-xs text-sm text-ink-muted">
              Upload a PDF, text, or Markdown file above, and I'll answer questions
              grounded in it.
            </p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} onOpenCitation={onOpenCitation} />
      ))}
      <div ref={endRef} />
    </div>
  )
}
