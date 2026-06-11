/**
 * In-memory mock of the documents API. Replays the documented JSON shapes and,
 * crucially, the status lifecycle (uploaded → ingesting → ready | failed) on a
 * timer so the polling UI can be developed before the backend is up.
 *
 * Enabled when VITE_USE_MOCKS === 'true' (see lib/api.ts). Off by default so a
 * plain `npm run dev` talks to the real api via the Vite proxy.
 */
import type { DocumentOut, DocumentStatus, Health } from './types'
import { MAX_UPLOAD_BYTES, precheckFile } from './upload-rules'

interface MockDoc extends DocumentOut {
  /** Wall-clock ms at which this doc should advance to its next status. */
  _nextAt: number
  _final: DocumentStatus
}

let seq = 100
const docs = new Map<number, MockDoc>()

function seed() {
  if (docs.size > 0) return
  const now = Date.now()
  const base = (over: Partial<MockDoc>): MockDoc => ({
    id: seq++,
    filename: 'untitled',
    status: 'ready',
    size: 0,
    mime: 'application/pdf',
    failure_reason: null,
    created_at: new Date(now).toISOString(),
    _nextAt: Infinity,
    _final: 'ready',
    ...over,
  })
  const samples: MockDoc[] = [
    base({
      filename: 'q3-earnings-report.pdf',
      size: 1_842_000,
      status: 'ready',
    }),
    base({
      filename: 'product-spec.md',
      size: 24_500,
      mime: 'text/markdown',
      status: 'ready',
    }),
    base({
      filename: 'corrupted-scan.pdf',
      size: 512_000,
      status: 'failed',
      failure_reason:
        'Could not extract text — the PDF appears to be an image-only scan.',
    }),
  ]
  for (const d of samples) docs.set(d.id, d)
}

/** Advance any docs whose timer has elapsed. Called on every read. */
function tick() {
  const now = Date.now()
  for (const d of docs.values()) {
    if (now < d._nextAt) continue
    if (d.status === 'uploaded') {
      d.status = 'ingesting'
      d._nextAt = now + 2600
    } else if (d.status === 'ingesting') {
      d.status = d._final
      if (d._final === 'failed') {
        d.failure_reason = 'Ingestion failed: embedding service returned an error.'
      }
      d._nextAt = Infinity
    }
  }
}

function strip(d: MockDoc): DocumentOut {
  const { _nextAt: _n, _final: _f, ...rest } = d
  void _n
  void _f
  return rest
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

export const mockApi = {
  async getHealth(): Promise<Health> {
    await delay(180)
    return {
      ok: true,
      version: '0.1.0-mock',
      services: { postgres: 'ok', qdrant: 'ok', openai: 'configured' },
    }
  },

  async listDocuments(): Promise<DocumentOut[]> {
    seed()
    tick()
    await delay(150)
    return [...docs.values()]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(strip)
  },

  async uploadDocument(
    file: File,
    onProgress?: (fraction: number) => void,
  ): Promise<DocumentOut> {
    const reason = precheckFile(file)
    if (reason) {
      const status = file.size > MAX_UPLOAD_BYTES ? 413 : 415
      throw Object.assign(new Error(reason), { status })
    }
    // Simulate a progress curve.
    for (let p = 0; p <= 1; p += 0.25) {
      onProgress?.(p)
      await delay(120)
    }
    seed()
    const now = Date.now()
    // Make any file literally named to fail, do so — handy for demoing errors.
    const willFail = /fail|corrupt/i.test(file.name)
    const doc: MockDoc = {
      id: seq++,
      filename: file.name,
      status: 'uploaded',
      size: file.size,
      mime: file.type || 'application/octet-stream',
      failure_reason: null,
      created_at: new Date(now).toISOString(),
      _nextAt: now + 1800,
      _final: willFail ? 'failed' : 'ready',
    }
    docs.set(doc.id, doc)
    return strip(doc)
  },

  async deleteDocument(id: number): Promise<void> {
    await delay(120)
    docs.delete(id)
  },
}
