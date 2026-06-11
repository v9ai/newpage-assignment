import { useToasts } from '../hooks/toast-context'
import type { ToastTone } from '../hooks/toast-context'

const toneStyles: Record<ToastTone, { bar: string; icon: string; glyph: string }> = {
  success: { bar: 'bg-ok', icon: 'text-ok', glyph: '✓' },
  error: { bar: 'bg-err', icon: 'text-err', glyph: '!' },
  info: { bar: 'bg-info', icon: 'text-info', glyph: 'i' },
}

export function Toaster() {
  const { toasts, dismiss } = useToasts()

  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-3 p-4 sm:inset-x-auto sm:right-0 sm:items-end"
      aria-live="polite"
      aria-atomic="false"
    >
      {toasts.map((t) => {
        const tone = toneStyles[t.tone]
        return (
          <div
            key={t.id}
            role={t.tone === 'error' ? 'alert' : 'status'}
            className="animate-toast-in pointer-events-auto flex w-full max-w-sm gap-3 overflow-hidden rounded-xl border border-border bg-surface-card shadow-pop"
          >
            <span className={`w-1 shrink-0 ${tone.bar}`} aria-hidden="true" />
            <div className="flex flex-1 items-start gap-3 py-3 pr-2">
              <span
                className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full text-xs font-bold ${tone.icon}`}
                aria-hidden="true"
              >
                {tone.glyph}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{t.title}</p>
                {t.description && (
                  <p className="mt-0.5 text-sm break-words text-ink-muted">
                    {t.description}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="shrink-0 px-3 text-ink-faint transition-colors hover:text-ink"
              aria-label="Dismiss notification"
            >
              ✕
            </button>
          </div>
        )
      })}
    </div>
  )
}
