# 08 — Document Parsing

**Roadmap phase:** 2 · **Depends on:** 07

## Goal
Uploaded files become clean extracted text with page provenance.

## Scope
- Install + pin LlamaIndex (first unit that needs it)
- LlamaIndex readers: PDF via `pypdf`; txt/md passthrough
- Extraction keeps page numbers (PDF) for later citations
- Corrupt/empty/encrypted files → document status `failed` with a stored reason, not a 500

## Done when
- Unit tests: a sample PDF and md extract expected text + page metadata
- A corrupt file ends in `failed` with a human-readable reason
