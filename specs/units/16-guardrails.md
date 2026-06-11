# 16 — Guardrails

**Roadmap phase:** 7 · **Depends on:** 13

## Goal
The assistant can't be talked out of its grounding — by users or by documents.

## Scope
- System prompt hardening: answer only from context; ignore instructions embedded inside documents (prompt injection defense)
- Input limits: max question length, sanitization; upload size caps enforced server-side (07 confirms)
- Injection test cases: a document containing "ignore previous instructions…" must not change behavior

## Done when
- Injection test suite passes (malicious doc + malicious question)
- Limits return clear 4xx errors, documented in OpenAPI
