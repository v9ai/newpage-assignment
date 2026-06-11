/**
 * Thin API client over the documents + health endpoints. Same-origin: in dev
 * the Vite proxy forwards /api/* to :8000; in prod nginx does the same.
 *
 * Flip to the in-memory mock by setting VITE_USE_MOCKS=true (e.g. run
 * `VITE_USE_MOCKS=true npm run dev`). Off by default.
 */
import { mockApi } from './mock'
import { ApiError } from './types'
import type { DocumentOut, Health } from './types'

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

async function detail(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // non-JSON error body
  }
  return `Request failed (${res.status})`
}

async function getHealth(): Promise<Health> {
  if (USE_MOCKS) return mockApi.getHealth()
  const res = await fetch('/api/health')
  if (!res.ok) throw new ApiError(res.status, await detail(res))
  return (await res.json()) as Health
}

async function listDocuments(): Promise<DocumentOut[]> {
  if (USE_MOCKS) return mockApi.listDocuments()
  const res = await fetch('/api/documents')
  if (!res.ok) throw new ApiError(res.status, await detail(res))
  return (await res.json()) as DocumentOut[]
}

/**
 * Upload via XHR so we can surface real progress events (fetch has no upload
 * progress). Resolves with the created DocumentOut, rejects with ApiError on
 * 4xx/5xx carrying the server's `detail`.
 */
function uploadDocument(
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<DocumentOut> {
  if (USE_MOCKS) return mockApi.uploadDocument(file, onProgress)
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/documents')
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) onProgress?.(e.loaded / e.total)
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentOut)
        } catch {
          reject(new ApiError(xhr.status, 'Malformed response from server.'))
        }
        return
      }
      let message = `Upload failed (${xhr.status})`
      try {
        const body = JSON.parse(xhr.responseText) as { detail?: string }
        if (body.detail) message = body.detail
      } catch {
        // keep default
      }
      reject(new ApiError(xhr.status, message))
    })
    xhr.addEventListener('error', () =>
      reject(new ApiError(0, 'Network error — is the API reachable?')),
    )
    xhr.addEventListener('abort', () =>
      reject(new ApiError(0, 'Upload cancelled.')),
    )
    xhr.send(form)
  })
}

async function deleteDocument(id: number): Promise<void> {
  if (USE_MOCKS) return mockApi.deleteDocument(id)
  const res = await fetch(`/api/documents/${id}`, { method: 'DELETE' })
  if (!res.ok && res.status !== 204) throw new ApiError(res.status, await detail(res))
}

export const api = {
  getHealth,
  listDocuments,
  uploadDocument,
  deleteDocument,
  usingMocks: USE_MOCKS,
}
