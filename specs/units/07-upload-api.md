# 07 — Upload API

**Roadmap phase:** 2 · **Depends on:** 03

## Goal
Documents can be uploaded and tracked in Postgres.

## Scope
- `POST /api/documents` (multipart): accept PDF, txt, md; persist file to a volume-backed dir
- Reject unsupported types and oversized files (size cap from config) with clear 4xx errors
- Document record: id, filename, size, mime, status (`uploaded`), created_at
- `GET /api/documents` list; `DELETE /api/documents/{id}`

## Done when
- pytest covers happy path + unsupported type + oversize rejection
- Uploaded file lands on disk; record visible via list endpoint
