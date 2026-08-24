"""
Production server launcher for LiuHao AI OS Y1.0
"""

import os
import sys
import uvicorn
from pathlib import Path

# Set production environment
os.environ["APP_ENV"] = "production"

# Load production .env
from dotenv import load_dotenv
env_file = Path(__file__).parent / ".env.production"
if env_file.exists():
    load_dotenv(env_file)
    print(f"[OK] Loaded production environment from {env_file}")
else:
    print(f"[WARN]  No .env.production found, using defaults")

# Configure logging
import structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    workers = int(os.getenv("API_WORKERS", "4"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    print("=" * 60)
    print("[START] LiuHao AI OS Y1.0 - Production Server")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Workers: {workers}")
    print(f"Log Level: {log_level}")
    print("=" * 60)
    
    # Start server
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level=log_level,
        access_log=True,
    )

