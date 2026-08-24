"""
Production server launcher for LiuHao AI OS Y1.0 - Single Worker Mode for Testing
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
    load_dotenv(env_file, override=True)
    print(f"[OK] Loaded production environment from {env_file}")
    # Verify critical env vars
    print(f"[ENV] APP_ENV={os.getenv('APP_ENV')}")
    print(f"[ENV] DATABASE_URL={os.getenv('DATABASE_URL')}")
    print(f"[ENV] SECRET_KEY length={len(os.getenv('SECRET_KEY', ''))}")
    print(f"[ENV] JWT_SECRET_KEY length={len(os.getenv('JWT_SECRET_KEY', ''))}")
else:
    print(f"[WARN] No .env.production found, using defaults")

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
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    print("=" * 60)
    print("[START] LiuHao AI OS Y1.0 - Production Server (Single Worker)")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Workers: 1 (single worker mode)")
    print(f"Log Level: {log_level}")
    print("=" * 60)
    
    # Start server with single worker
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        workers=1,  # Single worker to avoid env var issues
        reload=False,
        log_level=log_level,
        access_log=True,
    )
