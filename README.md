# DocChat

Ask questions about your documents. Get answers with citations — grounded strictly in what you uploaded.

Built for the Newpage Solutions fullstack AI take-home (Option 1: Chat With Your Docs).

## Demo

![DocChat demo — landing page with live service health](docs/media/demo.gif)

<sup>Recorded with Playwright against the running stack (`make video` re-records it —
source clip: [docs/media/demo.webm](docs/media/demo.webm)). Updated as features land.</sup>

## Quick start

Prerequisites: Docker, and an OpenAI API key.

```bash
cp .env.example .env.local   # then put your real OPENAI_API_KEY in .env.local
docker compose up --build
```

Open <http://localhost:3000>. The API is at <http://localhost:8000> (OpenAPI docs at `/docs`).

Want a demo corpus? `make fetch-samples` pulls 28 architecture docs into `samples/docs/` for uploading.

> Deployment target is **localhost via docker compose** — that is the entire run story.
> Productionization is discussed below, not implemented.

## Status

Spec-driven build in progress — see [`specs/`](specs/) for the roadmap and the 10 build units.

| Section | Status |
|---|---|
| Architecture overview | _placeholder — diagram lands with the build_ |
| Productionization (AWS/GCP/Azure/Cloudflare) | _placeholder_ |
| RAG/LLM approach & decisions | _placeholder — see `specs/tech-stack.md` meanwhile_ |
| Key technical decisions | _placeholder_ |
| Engineering standards followed & skipped | _placeholder_ |
| AI tools in the development process | _placeholder — `specs/` is the workflow exhibit_ |
| What I'd do differently with more time | _placeholder_ |
| Screenshots / video | Playwright-recorded demo above (`make video`); full walkthrough re-recorded after the chat UI phase |

## Development

```bash
make dev        # api with reload on :8000
make test       # backend tests
make typecheck  # mypy strict
make lint       # ruff
make migrate    # alembic upgrade head
```

Frontend: `cd web && npm run dev` (Vite on :5173, proxies /api to :8000).
