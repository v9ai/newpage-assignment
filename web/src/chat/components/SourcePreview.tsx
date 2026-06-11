import { useEffect, useRef } from 'react'
import type { Citation } from '../types'

interface Props {
  citation: Citation
  onClose: () => void
}

/**
 * Slide-over panel showing a citation's source passage (doc, page, chunk text).
 * Closes on Escape or backdrop click; traps initial focus on the close button.
 */
export function SourcePreview({ citation, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const where =
    citation.page != null
      ? `Page ${citation.page}`
      : `Chunk ${citation.chunk_index}`

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={`Source: ${citation.filename}`}
    >
      <button
        className="absolute inset-0 bg-ink/30 backdrop-blur-[1px]"
        onClick={onClose}
        aria-label="Close source preview"
        tabIndex={-1}
      />
      <div className="animate-toast-in relative flex h-full w-full max-w-md flex-col bg-surface-card shadow-pop">
        <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs font-medium tracking-wide text-accent uppercase">
              Source passage
            </p>
            <p className="mt-1 truncate font-semibold text-ink" title={citation.filename}>
              {citation.filename}
            </p>
            <p className="text-sm text-ink-muted">
              {where} · chunk #{citation.chunk_index}
            </p>
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            className="shrink-0 rounded-lg p-2 text-ink-faint transition-colors hover:bg-surface-sunken hover:text-ink"
            aria-label="Close"
          >
            ✕
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <blockquote className="border-l-2 border-accent-ring bg-surface-sunken/60 px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap text-ink">
            {citation.snippet}
          </blockquote>
        </div>
      </div>
    </div>
  )
}
