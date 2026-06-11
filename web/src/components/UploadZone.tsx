import { useCallback, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useToasts } from '../hooks/toast-context'
import { ApiError } from '../lib/types'
import { ACCEPT_ATTR, MAX_UPLOAD_MB, precheckFile } from '../lib/upload-rules'

interface InFlight {
  key: string
  name: string
  fraction: number
}

export function UploadZone({ onUploaded }: { onUploaded: () => void }) {
  const { push } = useToasts()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploads, setUploads] = useState<InFlight[]>([])
  const dragDepth = useRef(0)

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files)
      if (list.length === 0) return

      for (const file of list) {
        const reason = precheckFile(file)
        if (reason) {
          push({ tone: 'error', title: `Can't upload ${file.name}`, description: reason })
          continue
        }

        const key = `${file.name}-${file.size}-${Date.now()}-${Math.random()}`
        setUploads((prev) => [...prev, { key, name: file.name, fraction: 0 }])

        try {
          await api.uploadDocument(file, (fraction) => {
            setUploads((prev) =>
              prev.map((u) => (u.key === key ? { ...u, fraction } : u)),
            )
          })
          push({
            tone: 'success',
            title: 'Upload complete',
            description: `${file.name} is queued for ingestion.`,
          })
          onUploaded()
        } catch (e) {
          const description =
            e instanceof ApiError
              ? e.message
              : e instanceof Error
                ? e.message
                : 'Unexpected error while uploading.'
          push({ tone: 'error', title: `Upload failed: ${file.name}`, description })
        } finally {
          setUploads((prev) => prev.filter((u) => u.key !== key))
        }
      }
    },
    [push, onUploaded],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      dragDepth.current = 0
      setDragging(false)
      if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  return (
    <div className="w-full">
      <label
        onDragEnter={(e) => {
          e.preventDefault()
          dragDepth.current += 1
          setDragging(true)
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={(e) => {
          e.preventDefault()
          dragDepth.current -= 1
          if (dragDepth.current <= 0) setDragging(false)
        }}
        onDrop={onDrop}
        className={`group flex cursor-pointer flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging
            ? 'border-accent bg-accent-soft/60'
            : 'border-border-strong bg-surface-card/60 hover:border-accent hover:bg-accent-soft/30'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          multiple
          className="sr-only"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files)
            e.target.value = ''
          }}
        />
        <span
          className={`grid size-12 place-items-center rounded-full transition-colors ${
            dragging ? 'bg-accent text-white' : 'bg-accent-soft text-accent'
          }`}
          aria-hidden="true"
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 16V4M12 4l-4 4M12 4l4 4" />
            <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </span>
        <div>
          <p className="font-medium text-ink">
            {dragging ? 'Drop to upload' : 'Drag & drop documents here'}
          </p>
          <p className="mt-1 text-sm text-ink-muted">
            or{' '}
            <span className="font-medium text-accent underline-offset-2 group-hover:underline">
              browse files
            </span>{' '}
            · PDF, TXT, MD · up to {MAX_UPLOAD_MB} MB
          </p>
        </div>
      </label>

      {uploads.length > 0 && (
        <ul className="mt-4 space-y-2" aria-label="Uploads in progress">
          {uploads.map((u) => (
            <li
              key={u.key}
              className="rounded-lg border border-border bg-surface-card px-4 py-3"
            >
              <div className="flex items-center justify-between text-sm">
                <span className="truncate font-medium text-ink">{u.name}</span>
                <span className="ml-3 shrink-0 text-ink-muted">
                  {Math.round(u.fraction * 100)}%
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-200"
                  style={{ width: `${Math.max(4, u.fraction * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="sr-only" aria-live="polite">
        {uploads.length > 0
          ? `${uploads.length} upload${uploads.length > 1 ? 's' : ''} in progress`
          : ''}
      </p>
    </div>
  )
}
