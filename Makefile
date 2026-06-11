.PHONY: typecheck lint test dev fetch-samples

# Example ingestion corpus: architecture docs from github.com/v9ai/agentic-sales.
# Cloned shallow into samples/ (gitignored) — never vendored into this repo.
fetch-samples:
	@if [ ! -d samples/.agentic-sales ]; then \
		git clone --depth 1 https://github.com/v9ai/agentic-sales samples/.agentic-sales; \
	fi
	mkdir -p samples/docs
	cp samples/.agentic-sales/docs/*.md samples/docs/
	cp samples/.agentic-sales/README.md samples/docs/agentic-sales-README.md
	@echo "Sample corpus ready: $$(ls samples/docs | wc -l | tr -d ' ') markdown files in samples/docs/"

typecheck:
	cd api && uv run mypy

lint:
	cd api && uv run ruff check .

test:
	cd api && uv run pytest -q

dev:
	cd api && uv run uvicorn app.main:app --reload --port 8000

migrate:
	cd api && uv run alembic upgrade head

# Re-record the README demo (requires the stack: docker compose up)
video:
	cd web && node scripts/record-demo.mjs
	ffmpeg -y -i docs/media/demo.webm -vf "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 docs/media/demo.gif
	@ls -lh docs/media/
