# 05 — Upload API & Parsing

**Roadmap phase:** 2 · **Integration deps:** 02 · **Teammate:** `ingest` · *(merges old units 07 + 08)*

## Owns (files)
`api/app/documents.py`, `api/app/parsing.py`, `api/app/storage.py`, and their tests.
Router mount in `main.py` + LlamaIndex/pypdf pins → message the lead.

## Goal
Documents can be uploaded, tracked in Postgres, and turned into clean extracted text with
page provenance.

## Provides (contracts)
The documents endpoints and `DocumentOut` from the [shared contracts](README.md#shared-contracts),
plus the parsing output consumed by 06: per-document list of `{ text, page }` blocks.

## Scope
- `POST /api/documents` (multipart): accept PDF, txt, md; persist file to a volume-backed dir
- Reject unsupported types (415) and oversized files (413, cap from config) with clear errors
- Document record: id, filename, size, mime, status (`uploaded`), created_at
- `GET /api/documents` list; `DELETE /api/documents/{id}`
- Install + pin LlamaIndex (first unit that needs it)
- LlamaIndex readers: PDF via `pypdf`; txt/md passthrough
- Extraction keeps page numbers (PDF) for later citations
- Corrupt/empty/encrypted files → document status `failed` with a stored reason, not a 500

## Parallel notes
Routes and parsing are independent halves of this unit and can be built concurrently. Parsing
is pure (file in → text+pages out) and testable with no database; routes need only the
`documents` table contract — testable against a throwaway SQLite/pg fixture before 02 merges.

## Done when
- pytest covers happy path + unsupported type + oversize rejection
- Uploaded file lands on disk; record visible via list endpoint
- Unit tests: a sample PDF and md extract expected text + page metadata
- A corrupt file ends in `failed` with a human-readable reason
