import { api } from './lib/api'
import { useDocuments } from './hooks/useDocuments'
import { HealthBadge } from './components/HealthBadge'
import { UploadZone } from './components/UploadZone'
import { DocumentList } from './components/DocumentList'
import { ChatPanel } from './chat/ChatPanel'

export default function App() {
  const { documents, loading, error, refresh } = useDocuments()
  const hasDocuments = !!documents && documents.length > 0

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/70 bg-surface-card/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <span
              className="grid size-8 place-items-center rounded-lg bg-accent text-white shadow-card"
              aria-hidden="true"
            >
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
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </span>
            <span className="text-lg font-semibold tracking-tight text-ink">
              Doc<span className="text-accent">Chat</span>
            </span>
          </div>
          {api.usingMocks && (
            <span className="rounded-full bg-warn-soft px-2.5 py-1 text-xs font-medium text-warn">
              mock data
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <section className="animate-rise mb-8 text-center lg:text-left">
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
            Ask questions about your documents
          </h1>
          <p className="mt-2 text-ink-muted">
            Upload PDFs, text, or Markdown and get grounded answers with citations
            back to the source passage.
          </p>
        </section>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          {/* Documents column */}
          <div className="animate-rise flex flex-col gap-6" style={{ animationDelay: '40ms' }}>
            <HealthBadge />
            <UploadZone onUploaded={refresh} />
            <DocumentList
              documents={documents}
              loading={loading}
              error={error}
              onChanged={refresh}
            />
          </div>

          {/* Chat column */}
          <div className="animate-rise" style={{ animationDelay: '100ms' }}>
            <ChatPanel hasDocuments={hasDocuments} />
          </div>
        </div>
      </main>

      <footer className="mx-auto max-w-6xl px-6 pb-10 text-center text-xs text-ink-faint">
        DocChat · retrieval-augmented document chat
      </footer>
    </div>
  )
}
