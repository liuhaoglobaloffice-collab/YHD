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
from src.core.errors import (
    ResourceNotFoundError,
    PermissionDeniedError,
    AuthenticationError,
    ValidationError as LiuHaoValidationError,
)
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
        # 映射错误类型到 HTTP 状态码
        if isinstance(exc, ResourceNotFoundError):
            http_status = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, PermissionDeniedError):
            http_status = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, AuthenticationError):
            http_status = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, LiuHaoValidationError):
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            http_status = status.HTTP_400_BAD_REQUEST

        return JSONResponse(
            status_code=http_status,
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

    # Expose Prometheus metrics at root /metrics as well as under /api/v1/metrics
    try:
        from src.api.routes import metrics as metrics_module
        app.include_router(metrics_module.router)
    except Exception:
        # if metrics module cannot be loaded, continue without it
        logger.info("metrics_router_not_loaded")

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

