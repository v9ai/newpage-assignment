import type { Citation } from '../types'

interface Props {
  citation: Citation
  index: number
  onOpen: (citation: Citation) => void
}

/**
 * A numbered, clickable source reference shown under an assistant answer.
 * Clicking opens the source preview with the exact passage.
 */
export function CitationChip({ citation, index, onOpen }: Props) {
  const where =
    citation.page != null ? `p.${citation.page}` : `#${citation.chunk_index}`
  return (
    <button
      onClick={() => onOpen(citation)}
      className="group inline-flex max-w-full items-center gap-1.5 rounded-full border border-border bg-surface-card px-2.5 py-1 text-xs text-ink-muted transition-colors hover:border-accent hover:bg-accent-soft/40 hover:text-accent focus-visible:border-accent focus-visible:text-accent"
      title={`${citation.filename} · ${where}`}
    >
      <span className="grid size-4 shrink-0 place-items-center rounded-full bg-accent-soft text-[10px] font-semibold text-accent">
        {index + 1}
      </span>
      <span className="truncate font-medium">{citation.filename}</span>
      <span className="shrink-0 text-ink-faint">{where}</span>
    </button>
  )
}
