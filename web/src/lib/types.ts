/**
 * Shared types mirroring the live API (api/app/documents.py, api/app/main.py).
 *
 * The API serializes `DocumentOut` per the README contract: `size` and
 * `failure_reason` keys (aliased from the `size_bytes`/`error` columns
 * server-side) with integer ids. We consume exactly that JSON shape.
 */

export type DocumentStatus = 'uploaded' | 'ingesting' | 'ready' | 'failed'

export interface DocumentOut {
  id: number
  filename: string
  status: DocumentStatus
  size: number
  mime: string
  /** Failure reason; non-null only when status === 'failed'. */
  failure_reason: string | null
  created_at: string
}

export type ServiceStatus =
  | 'ok'
  | 'error'
  | 'configured'
  | 'missing'
  | 'unreachable'

export interface Health {
  ok: boolean
  version: string
  services: {
    postgres: ServiceStatus
    qdrant: ServiceStatus
    openai: ServiceStatus
  }
}

/** Error thrown by the API client carrying the server's HTTP status + detail. */
export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}
