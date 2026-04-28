#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
VENV_PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"

cd "$REPO_ROOT"

if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

if [[ -x "$VENV_PYTHON" ]]; then
    exec "$VENV_PYTHON" main.py
fi

exec python main.py
