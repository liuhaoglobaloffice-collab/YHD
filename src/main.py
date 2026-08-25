"""
Main entry point for LiuHao AI OS
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables early - before any imports that use config
env = os.getenv("APP_ENV", "development")
if env == "production":
    env_file = Path(__file__).parent.parent / ".env.production"
    if env_file.exists():
        load_dotenv(env_file)
else:
    load_dotenv()  # Load .env if exists

import structlog
import uvicorn

from src.api.app import create_app
from src.core.config import get_settings

logger = structlog.get_logger(__name__)

# Create app instance for uvicorn
app = create_app()


def main():
    """Start the application"""
    settings = get_settings()

    logger.info(
        "starting_application",
        host=settings.app_host,
        port=settings.app_port,
        env=settings.app_env,
    )

    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
