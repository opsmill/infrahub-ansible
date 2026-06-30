#!/usr/bin/env bash
set -euo pipefail

# Ensure the project virtualenv exists and is exported into the session.
# Kept minimal: dev/integration dependency groups have incompatible transitive
# pins, so we do not run `uv sync` here — just guarantee a venv is present.

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
VENV_PATH="$REPO_ROOT/.venv"

if [ ! -d "$VENV_PATH" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv "$VENV_PATH" >&2
  else
    echo "session-start hook: 'uv' not found on PATH; skipping venv creation" >&2
    exit 0
  fi
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  printf 'export VIRTUAL_ENV=%q\n' "$VENV_PATH" >> "$CLAUDE_ENV_FILE"
  printf 'export PATH=%q:$PATH\n' "$VENV_PATH/bin" >> "$CLAUDE_ENV_FILE"
fi
