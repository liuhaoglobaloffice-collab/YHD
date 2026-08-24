# Stage 1 Setup and Run Guide

## Prerequisites

- Python 3.11+
- Docker Desktop (for PostgreSQL and Redis)
- Git

## Setup Steps

### 1. Create Virtual Environment

```bash
cd D:\LiuHao-AI-OS
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Start Database Services

```bash
docker-compose up -d
```

Wait for services to be healthy:
```bash
docker-compose ps
```

### 5. Create Environment Configuration

Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```

Edit `.env` and set secure values:
- `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `JWT_SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `POSTGRES_PASSWORD` (set to match docker-compose.yml)

**CRITICAL:** Never commit `.env` to Git!

### 6. Initialize Database

The database will be automatically initialized on first startup.

### 7. Start Application

```bash
python -m src.main
```

Or with uvicorn directly:
```bash
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### 8. Verify Health

Open browser to:
- http://localhost:8000/
- http://localhost:8000/api/v1/health/
- http://localhost:8000/api/v1/health/system

### 9. Run Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=src --cov-report=html
```

## API Documentation

Interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Stopping Services

```bash
# Stop application: Ctrl+C

# Stop database services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Development Workflow

1. Make code changes
2. Run tests: `pytest`
3. Check code style: `black src tests` and `ruff check src tests`
4. Run application with `--reload` for auto-restart on changes

## Security Notes

- All secrets must be in `.env` file (never in code)
- `.env` is in `.gitignore` (never commit secrets)
- Default policies are DENY (Fail Closed)
- All external features are disabled by default

## Stage 1 Scope

✅ Completed:
- Layer 0: Core Runtime (Config, Events, Errors, Logging, Lifecycle)
- Layer 1: Security & Governance (Policy Engine, Secrets Management)
- Layer 2: Identity & Access (Basic Auth, RBAC, Audit)
- Health Check API
- Database setup
- Testing framework

❌ Not in Stage 1:
- Provider Gateway (Stage 3)
- Network/Browser Gateway (Stage 5)
- Workflow Engine (Stage 5)
- Business OS (Stage 7)
- CEO Command Center (Stage 8)
