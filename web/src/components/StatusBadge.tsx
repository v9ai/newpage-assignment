import type { DocumentStatus } from '../lib/types'

interface Meta {
  label: string
  className: string
  spinning?: boolean
}

const META: Record<DocumentStatus, Meta> = {
  uploaded: {
    label: 'Queued',
    className: 'bg-surface-sunken text-ink-muted ring-border-strong',
  },
  ingesting: {
    label: 'Ingesting',
    className: 'bg-info-soft text-info ring-info/30',
    spinning: true,
  },
  ready: {
    label: 'Ready',
    className: 'bg-ok-soft text-ok ring-ok/30',
  },
  failed: {
    label: 'Failed',
    className: 'bg-err-soft text-err ring-err/30',
  },
}

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const meta = META[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${meta.className}`}
    >
      {meta.spinning ? (
        <span
          className="size-2.5 animate-spin rounded-full border-[1.5px] border-current border-t-transparent"
          aria-hidden="true"
        />
      ) : (
        <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      )}
      {meta.label}
    </span>
  )
}
