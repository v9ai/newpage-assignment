import { useEffect, useRef, useState } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
  /** Disables input entirely (e.g. no documents to chat about yet). */
  blocked?: boolean
  placeholder?: string
}

/**
 * Message composer: Enter sends, Shift+Enter inserts a newline. Auto-grows up
 * to a few lines, refocuses after sending, and disables while a turn streams.
 */
export function Composer({ onSend, disabled, blocked, placeholder }: Props) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  // Auto-resize to content.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [value])

  // Refocus once a streaming turn finishes.
  useEffect(() => {
    if (!disabled && !blocked) ref.current?.focus()
  }, [disabled, blocked])

  const submit = () => {
    const text = value.trim()
    if (!text || disabled || blocked) return
    onSend(text)
    setValue('')
  }

  return (
    <div className="border-t border-border bg-surface-card/80 p-3 backdrop-blur">
      <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface-card px-3 py-2 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent-ring">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          disabled={blocked}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder={
            blocked
              ? 'Upload a document to start chatting…'
              : (placeholder ?? 'Ask a question about your documents…')
          }
          className="max-h-40 flex-1 resize-none bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint disabled:cursor-not-allowed"
          aria-label="Message"
        />
        <button
          onClick={submit}
          disabled={disabled || blocked || value.trim().length === 0}
          className="grid size-9 shrink-0 place-items-center rounded-xl bg-accent text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="Send message"
        >
          {disabled ? (
            <span className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          )}
        </button>
      </div>
      <p className="mt-1.5 px-1 text-[11px] text-ink-faint">
        Enter to send · Shift+Enter for a new line
      </p>
    </div>
  )
}
