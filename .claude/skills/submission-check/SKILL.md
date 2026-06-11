---
name: submission-check
description: >
  Audit the repo against assignment.md's "What to Submit" and "What We're
  Looking For" checklists before handing in: README sections, setup-from-clean
  story, screenshots/video, eval/e2e status, and uncommitted work. Use when the
  user asks "is this ready to submit?" or wants a gap list near the deadline.
---

# Pre-submission audit against assignment.md

Read `assignment.md` fresh — it is the rubric. Then verify each deliverable exists and
is current, not just present.

## Checklist to walk

1. **README completeness** — assignment.md requires, as distinct content: quick setup,
   architecture overview, productionization path (AWS/GCP/Azure/Cloudflare — discussed,
   not implemented, which the README already states), RAG/LLM choices considered and
   final (LLM, embeddings, vector DB, orchestration, prompt & context management,
   guardrails, quality, observability), key technical decisions with reasons,
   engineering standards followed and skipped, AI-tool usage in development, and
   what-with-more-time. Map each bullet to an actual README section; list any missing.
2. **Voice check** — the assignment says twice that the README must reflect the
   author's thinking, "not an LLM's direct output". Flag sections that read like
   generated boilerplate, but do NOT rewrite them yourself — that would recreate the
   problem. Tell the user which sections need their own words.
3. **Fresh-clone story** — the quick-start must hold from a clean checkout: every file
   it references exists (`.env.example`, compose file), `make fetch-samples` works, and
   nothing assumes state only this machine has. If feasible, actually rehearse it in a
   temp clone; otherwise trace it step by step and say which steps were only traced.
4. **Screenshots / video** — `docs/media/` must contain a current demo
   (`make video` re-records the gif and webm; requires the stack up). Check media
   freshness against recent UI commits — a demo showing an older UI counts as a gap.
5. **Quality gates green** — `make typecheck`, `make lint`, `make test` must pass now.
   `make eval` and `make e2e` need the stack and a real API key; report their last
   known status if running them is not feasible, and say so explicitly.
6. **Repo hygiene** — `git status` clean or explainable; no secrets committed
   (`.env.local` gitignored, no key material in history of touched files); `samples/`
   corpus not vendored (it is fetched, by design).

## Reporting

Produce a gap list ordered by what would cost the most in review: missing README rubric
items first, broken fresh-clone steps second, stale demo media third, red gates fourth.
For each gap give the fix and roughly how long it takes. End with a single
ready/not-ready verdict.
