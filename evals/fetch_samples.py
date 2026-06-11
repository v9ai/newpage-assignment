"""Fetch the golden-set sample corpus into samples/docs/ (idempotent).

The corpus is the architecture docs from github.com/v9ai/agentic-sales. It is
never vendored into this repo (samples/ is gitignored); `make fetch-samples`
runs this to populate it on a fresh clone. If the docs are already present the
script is a no-op so it is safe to run before every eval.

Usage: python evals/fetch_samples.py [--force]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/v9ai/agentic-sales.git"
# Markdown docs live under this path in the source repo.
SOURCE_SUBDIR = "docs"
EXPECTED_MIN_DOCS = 20

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST_DIR = REPO_ROOT / "samples" / "docs"


def _existing_md(dest: Path) -> list[Path]:
    return sorted(dest.glob("*.md")) if dest.exists() else []


def fetch(force: bool = False) -> int:
    existing = _existing_md(DEST_DIR)
    if existing and not force:
        print(f"samples present ({len(existing)} md files in {DEST_DIR}); skipping fetch.")
        return 0

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        print(f"cloning {REPO_URL} ...")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", REPO_URL, tmp],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"clone failed: {exc.stderr.strip()}", file=sys.stderr)
            return 1

        src = Path(tmp) / SOURCE_SUBDIR
        if not src.exists():
            # Fall back to repo root if the docs subdir layout changed upstream.
            src = Path(tmp)
        md_files = sorted(src.rglob("*.md"))
        if not md_files:
            print("no markdown docs found in the cloned repo", file=sys.stderr)
            return 1

        copied = 0
        for f in md_files:
            (DEST_DIR / f.name).write_bytes(f.read_bytes())
            copied += 1
        print(f"copied {copied} md files into {DEST_DIR}")

    final = _existing_md(DEST_DIR)
    if len(final) < EXPECTED_MIN_DOCS:
        print(
            f"warning: expected >= {EXPECTED_MIN_DOCS} docs, found {len(final)}",
            file=sys.stderr,
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch the eval sample corpus.")
    parser.add_argument("--force", action="store_true", help="re-fetch even if present")
    args = parser.parse_args()
    return fetch(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
