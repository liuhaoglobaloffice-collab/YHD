"""
FastAPI application initialization
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.api.dependencies.database import close_database, init_database
from src.api.routes import api_router
from src.core.config import get_settings
from src.core.errors import LiuHaoError
from src.core.lifecycle import get_lifecycle_manager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    lifecycle = get_lifecycle_manager()
    await lifecycle.startup()

    # Initialize database
    await init_database()
    logger.info("api_startup_complete")

    yield

    # Shutdown
    await close_database()
    await lifecycle.shutdown()
    logger.info("api_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="LiuHao AI OS",
        description="CEO-First Enterprise AI Operating System",
        version=__version__,
        lifespan=lifespan,
        debug=settings.app_debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(LiuHaoError)
    async def liuhao_error_handler(request: Request, exc: LiuHaoError):
        """Handle LiuHao-specific errors"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    # Include API routes
    app.include_router(api_router)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "LiuHao AI OS",
            "version": __version__,
            "status": "running",
        }

    return app
