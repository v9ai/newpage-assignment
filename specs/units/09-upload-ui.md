# 09 — Upload UI

**Roadmap phase:** 2 · **Depends on:** 05, 07

## Goal
Drag-and-drop upload with a live document list.

## Scope
- Drag-and-drop zone + file picker; client-side type/size pre-check mirroring server rules
- Document list: filename, size, status badge, delete
- Upload progress + error toasts (unsupported type, too large, server error)

## Done when
- Upload a PDF in the browser → appears in the list with status
- Rejection paths show friendly errors, not console traces
