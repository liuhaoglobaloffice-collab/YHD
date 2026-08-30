#!/usr/bin/env bash
set -e

export SECRET_KEY="${SECRET_KEY:-01234567890123456789012345678901}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-abcdefghijklmnopqrstuvwxyz1234567890ABCDEF}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./dev.db}"

# 应用入口：src.main:app（src/api/app.py 只暴露 create_app() 工厂，无模块级 app）
exec uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
