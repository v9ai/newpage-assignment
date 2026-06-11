/**
 * Client-side upload pre-checks that mirror the server's rules
 * (api/app/documents.py: ALLOWED_TYPES + max_upload_mb). The server is still
 * the source of truth — these only spare the user an obvious round-trip and a
 * raw 4xx.
 */

export const ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.md'] as const

/** Mirrors `Settings.max_upload_mb` (default 25). */
export const MAX_UPLOAD_MB = 25
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

/** Accept attribute for the native file input. */
export const ACCEPT_ATTR = '.pdf,.txt,.md,application/pdf,text/plain,text/markdown'

function extensionOf(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot === -1 ? '' : filename.slice(dot).toLowerCase()
}

export interface PrecheckRejection {
  filename: string
  reason: string
}

/**
 * Returns a human rejection reason, or null if the file passes the pre-check.
 */
export function precheckFile(file: File): string | null {
  const ext = extensionOf(file.name)
  if (!(ALLOWED_EXTENSIONS as readonly string[]).includes(ext)) {
    return `Unsupported file type "${ext || 'unknown'}". Allowed: PDF, TXT, MD.`
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `File is ${formatBytes(file.size)} — larger than the ${MAX_UPLOAD_MB} MB limit.`
  }
  return null
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unit]}`
}
