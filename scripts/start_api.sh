#!/usr/bin/env bash
set -e

export SECRET_KEY="${SECRET_KEY:-01234567890123456789012345678901}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-abcdefghijklmnopqrstuvwxyz1234567890ABCDEF}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./dev.db}"

uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
