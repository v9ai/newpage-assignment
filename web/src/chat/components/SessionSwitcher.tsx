import type { SessionSummary } from '../types'

interface Props {
  sessions: SessionSummary[]
  activeId: number | null
  onSelect: (id: number) => void
  onNew: () => void
}

/**
 * Horizontal session switcher with a "new chat" action. Compact so it works on
 * mobile; the active session is highlighted.
 */
export function SessionSwitcher({ sessions, activeId, onSelect, onNew }: Props) {
  return (
    <div className="flex items-center gap-2 border-b border-border px-3 py-2">
      <button
        onClick={onNew}
        className="flex shrink-0 items-center gap-1.5 rounded-lg bg-accent px-2.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-hover"
      >
        <span aria-hidden="true" className="text-sm leading-none">
          +
        </span>
        New
      </button>
      <div
        className="flex flex-1 gap-1.5 overflow-x-auto"
        role="tablist"
        aria-label="Chat sessions"
      >
        {sessions.length === 0 ? (
          <span className="px-1 py-1.5 text-xs text-ink-faint">No chats yet</span>
        ) : (
          sessions.map((s) => {
            const active = s.id === activeId
            return (
              <button
                key={s.id}
                role="tab"
                aria-selected={active}
                onClick={() => onSelect(s.id)}
                title={s.title}
                className={`max-w-[12rem] shrink-0 truncate rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-accent-soft text-accent'
                    : 'text-ink-muted hover:bg-surface-sunken hover:text-ink'
                }`}
              >
                {s.title || 'Untitled chat'}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
