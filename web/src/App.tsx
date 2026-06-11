import { api } from './lib/api'
import { useDocuments } from './hooks/useDocuments'
import { HealthBadge } from './components/HealthBadge'
import { UploadZone } from './components/UploadZone'
import { DocumentList } from './components/DocumentList'

export default function App() {
  const { documents, loading, error, refresh } = useDocuments()

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/70 bg-surface-card/60 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
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

      <main className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-10">
        <section className="animate-rise text-center">
          <h1 className="text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Ask questions about your documents
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-ink-muted">
            Upload PDFs, text, or Markdown and get grounded answers with citations
            back to the source passage.
          </p>
        </section>

        <div className="animate-rise" style={{ animationDelay: '40ms' }}>
          <HealthBadge />
        </div>

        <div className="animate-rise" style={{ animationDelay: '80ms' }}>
          <UploadZone onUploaded={refresh} />
        </div>

        <div className="animate-rise" style={{ animationDelay: '120ms' }}>
          <DocumentList
            documents={documents}
            loading={loading}
            error={error}
            onChanged={refresh}
          />
        </div>
      </main>

      <footer className="mx-auto max-w-3xl px-6 pb-10 text-center text-xs text-ink-faint">
        DocChat · retrieval-augmented document chat
      </footer>
    </div>
  )
}
