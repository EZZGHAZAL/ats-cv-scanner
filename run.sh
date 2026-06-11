#!/usr/bin/env bash
set -euo pipefail

# Convenience launcher for local development.
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
