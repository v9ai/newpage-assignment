import type { Citation, ChatMessage } from '../types'
import { CitationChip } from './CitationChip'

interface Props {
  message: ChatMessage
  onOpenCitation: (c: Citation) => void
}

/** True when the assistant streamed an answer but grounded it in no sources. */
function isRefusal(m: ChatMessage): boolean {
  return (
    m.role === 'assistant' &&
    !m.streaming &&
    !m.errored &&
    m.content.length > 0 &&
    m.citations.length === 0
  )
}

export function MessageBubble({ message, onOpenCitation }: Props) {
  const isUser = message.role === 'user'
  const refusal = isRefusal(message)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[85%] flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={[
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
            isUser
              ? 'bg-accent text-white'
              : message.errored
                ? 'border border-err/30 bg-err-soft text-ink'
                : refusal
                  ? 'border border-warn/30 bg-warn-soft/60 text-ink'
                  : 'border border-border bg-surface-card text-ink',
          ].join(' ')}
        >
          {message.errored && (
            <span className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-err">
              <span aria-hidden="true">⚠</span> Couldn't complete this answer
            </span>
          )}
          {message.content}
          {message.streaming && (
            <span
              className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse-soft rounded-sm bg-current align-middle"
              aria-label="assistant is typing"
            />
          )}
        </div>

        {refusal && (
          <span className="px-1 text-xs text-ink-faint">
            No matching passages were found in your documents.
          </span>
        )}

        {message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.citations.map((c, i) => (
              <CitationChip
                key={`${c.doc_id}-${c.chunk_index}-${i}`}
                citation={c}
                index={i}
                onOpen={onOpenCitation}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
