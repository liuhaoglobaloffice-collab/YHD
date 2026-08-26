CI Secrets and Local Test Instructions

This document explains how to provide the minimal secrets required to run the CI and how to run tests locally.

Required environment variables (CI and local testing):

- SECRET_KEY: Application secret for config/sessions.
- JWT_SECRET_KEY: JWT signing secret used by the app.
- DATABASE_URL: SQLAlchemy database URL (e.g., sqlite+aiosqlite:///./dev.db or postgres://user:pass@host/dbname)

Local testing:

1. Create a virtual environment and activate it:
   python -m venv .venv
   .\.venv\Scripts\activate

2. Install dependencies:
   pip install -r requirements.txt

3. Export required env vars (Windows PowerShell example):
   $env:SECRET_KEY = "test-secret"
   $env:JWT_SECRET_KEY = "test-jwt-secret"
   $env:DATABASE_URL = "sqlite+aiosqlite:///./dev.db"

4. Run tests:
   pytest -q

GitHub Actions:

- Add the following repository secrets in GitHub settings -> Secrets:
  - SECRET_KEY
  - JWT_SECRET_KEY
  - DATABASE_URL

The workflow '.github/workflows/ci.yml' will run the full test suite using these secrets.
