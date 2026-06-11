import { useState } from 'react'
import { api } from '../lib/api'
import { useToasts } from '../hooks/toast-context'
import { formatBytes } from '../lib/upload-rules'
import type { DocumentOut } from '../lib/types'
import { StatusBadge } from './StatusBadge'

function FileGlyph({ filename }: { filename: string }) {
  const ext = filename.slice(filename.lastIndexOf('.') + 1).toLowerCase()
  const tint =
    ext === 'pdf'
      ? 'bg-err-soft text-err'
      : ext === 'md'
        ? 'bg-accent-soft text-accent'
        : 'bg-info-soft text-info'
  return (
    <span
      className={`grid size-10 shrink-0 place-items-center rounded-lg text-[10px] font-bold tracking-wide ${tint}`}
      aria-hidden="true"
    >
      {ext.toUpperCase().slice(0, 3) || 'DOC'}
    </span>
  )
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function DocumentRow({
  doc,
  onDeleted,
}: {
  doc: DocumentOut
  onDeleted: () => void
}) {
  const { push } = useToasts()
  const [deleting, setDeleting] = useState(false)

  const remove = async () => {
    if (!window.confirm(`Delete "${doc.filename}"? This can't be undone.`)) return
    setDeleting(true)
    try {
      await api.deleteDocument(doc.id)
      push({ tone: 'info', title: 'Document deleted', description: doc.filename })
      onDeleted()
    } catch (e) {
      push({
        tone: 'error',
        title: 'Delete failed',
        description: e instanceof Error ? e.message : 'Could not delete document.',
      })
      setDeleting(false)
    }
  }

  return (
    <li
      className={`flex items-center gap-4 px-4 py-3 transition-opacity ${
        deleting ? 'pointer-events-none opacity-50' : ''
      }`}
    >
      <FileGlyph filename={doc.filename} />
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-ink" title={doc.filename}>
          {doc.filename}
        </p>
        <p className="mt-0.5 text-xs text-ink-muted">
          {formatBytes(doc.size)}
          {doc.created_at && <> · {formatDate(doc.created_at)}</>}
        </p>
        {doc.status === 'failed' && doc.failure_reason && (
          <p className="mt-1.5 rounded-md bg-err-soft px-2 py-1 text-xs text-err">
            {doc.failure_reason}
          </p>
        )}
      </div>
      <StatusBadge status={doc.status} />
      <button
        onClick={remove}
        disabled={deleting}
        className="shrink-0 rounded-lg p-2 text-ink-faint transition-colors hover:bg-err-soft hover:text-err focus-visible:bg-err-soft focus-visible:text-err"
        aria-label={`Delete ${doc.filename}`}
        title="Delete"
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
          <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
          <path d="M10 11v6M14 11v6" />
        </svg>
      </button>
    </li>
  )
}

interface Props {
  documents: DocumentOut[] | null
  loading: boolean
  error: string | null
  onChanged: () => void
}

export function DocumentList({ documents, loading, error, onChanged }: Props) {
  return (
    <section
      className="w-full rounded-card border border-border bg-surface-card/80 shadow-card backdrop-blur"
      aria-label="Your documents"
    >
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-ink">Your documents</h2>
        {documents && documents.length > 0 && (
          <span className="rounded-full bg-surface-sunken px-2 py-0.5 text-xs font-medium text-ink-muted">
            {documents.length}
          </span>
        )}
      </header>

      {error && !documents ? (
        <div className="px-4 py-10 text-center">
          <p className="text-sm font-medium text-err">Couldn't load documents</p>
          <p className="mt-1 text-sm text-ink-muted">{error}</p>
          <button
            onClick={onChanged}
            className="mt-4 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:bg-surface-sunken"
          >
            Retry
          </button>
        </div>
      ) : loading && !documents ? (
        <ul className="divide-y divide-border" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <li key={i} className="flex items-center gap-4 px-4 py-3">
              <span className="size-10 shrink-0 animate-pulse-soft rounded-lg bg-surface-sunken" />
              <div className="flex-1 space-y-2">
                <span className="block h-3.5 w-1/2 animate-pulse-soft rounded bg-surface-sunken" />
                <span className="block h-2.5 w-1/4 animate-pulse-soft rounded bg-surface-sunken" />
              </div>
              <span className="h-6 w-16 animate-pulse-soft rounded-full bg-surface-sunken" />
            </li>
          ))}
        </ul>
      ) : documents && documents.length === 0 ? (
        <div className="px-4 py-12 text-center">
          <span
            className="mx-auto grid size-12 place-items-center rounded-full bg-surface-sunken text-ink-faint"
            aria-hidden="true"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
            </svg>
          </span>
          <p className="mt-3 text-sm font-medium text-ink">No documents yet</p>
          <p className="mt-1 text-sm text-ink-muted">
            Upload a PDF, TXT, or Markdown file to get started.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {documents?.map((doc) => (
            <DocumentRow key={doc.id} doc={doc} onDeleted={onChanged} />
          ))}
        </ul>
      )}
    </section>
  )
}
