import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { DocumentOut } from '../lib/types'

/** Statuses that are still settling and warrant fast polling. */
const ACTIVE: ReadonlySet<string> = new Set(['uploaded', 'ingesting'])

const FAST_POLL_MS = 1500
const IDLE_POLL_MS = 8000

interface UseDocuments {
  documents: DocumentOut[] | null
  error: string | null
  loading: boolean
  /** Fetch now and re-evaluate the poll cadence (e.g. just after an upload). */
  refresh: () => void
}

/**
 * Loads the document list and keeps it fresh by polling. Polls quickly while
 * any document is mid-ingestion, then backs off so an idle list isn't hammered.
 * A single self-rescheduling loop drives both the initial load and refreshes,
 * so calling `refresh()` after an upload immediately switches to fast cadence.
 */
export function useDocuments(): UseDocuments {
  const [documents, setDocuments] = useState<DocumentOut[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const timer = useRef<number | undefined>(undefined)
  const cancelled = useRef(false)
  // Holds the latest loop function so `refresh` can invoke it without being a
  // dependency itself (keeps refresh stable across renders).
  const runRef = useRef<() => void>(() => {})

  useEffect(() => {
    cancelled.current = false

    const run = async () => {
      if (timer.current) window.clearTimeout(timer.current)
      try {
        const docs = await api.listDocuments()
        if (cancelled.current) return
        setDocuments(docs)
        setError(null)
        const hasActive = docs.some((d) => ACTIVE.has(d.status))
        timer.current = window.setTimeout(
          run,
          hasActive ? FAST_POLL_MS : IDLE_POLL_MS,
        )
      } catch (e) {
        if (cancelled.current) return
        setError(e instanceof Error ? e.message : 'Could not load documents.')
        timer.current = window.setTimeout(run, IDLE_POLL_MS)
      } finally {
        if (!cancelled.current) setLoading(false)
      }
    }

    runRef.current = run
    run()

    return () => {
      cancelled.current = true
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])

  const refresh = useCallback(() => {
    runRef.current()
  }, [])

  return { documents, error, loading, refresh }
}
