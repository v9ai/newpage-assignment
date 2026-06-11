# 05 — Frontend Scaffold

**Roadmap phase:** 1 · **Depends on:** 01

## Goal
A branded React SPA skeleton proving frontend↔backend wiring.

## Scope
- Init `web/` with Vite + React + TS (strict) + Tailwind; exact-pinned versions (no `^`)
- Base design tokens (colors, type scale, spacing) — visibly not the Vite default
- Landing page: app name, tagline, disabled upload placeholder
- Fetch and display `/api/health` status (green/red indicator)

## Done when
- `npm run build` and strict `tsc` pass
- Browser shows the landing page with live health status
