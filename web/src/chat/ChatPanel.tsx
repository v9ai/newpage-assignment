import { useState } from 'react'
import { useChat } from './useChat'
import type { Citation } from './types'
import { SessionSwitcher } from './components/SessionSwitcher'
import { MessageList } from './components/MessageList'
import { Composer } from './components/Composer'
import { SourcePreview } from './components/SourcePreview'

interface Props {
  /** Whether any document exists yet — gates the composer + empty-state copy. */
  hasDocuments: boolean
}

/**
 * The full chat experience: session switcher, streamed message history with
 * citations, a source-preview slide-over, and the composer. Self-contained —
 * drop it next to the document panel.
 */
export function ChatPanel({ hasDocuments }: Props) {
  const {
    sessions,
    activeId,
    messages,
    streaming,
    sessionsError,
    selectSession,
    newSession,
    send,
  } = useChat()
  const [preview, setPreview] = useState<Citation | null>(null)

  return (
    <section
      className="flex h-[min(70vh,640px)] w-full flex-col overflow-hidden rounded-card border border-border bg-surface-card/80 shadow-card backdrop-blur"
      aria-label="Chat"
    >
      <SessionSwitcher
        sessions={sessions}
        activeId={activeId}
        onSelect={selectSession}
        onNew={() => void newSession()}
      />

      {sessionsError && (
        <p
          role="alert"
          className="border-b border-err/20 bg-err-soft px-4 py-2 text-xs text-err"
        >
          {sessionsError}
        </p>
      )}

      <MessageList
        messages={messages}
        hasDocuments={hasDocuments}
        onOpenCitation={setPreview}
      />

      <Composer onSend={(t) => void send(t)} disabled={streaming} blocked={!hasDocuments} />

      {preview && (
        <SourcePreview citation={preview} onClose={() => setPreview(null)} />
      )}
    </section>
  )
}
