import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import health, knowledge, assessment, chat, scenarios
from app.config import settings
from app.database.init_db import init_db

logger = logging.getLogger("darukaa.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle context manager."""
    logger.info("Initializing database schema and pgvector extension...")
    try:
        init_db(seed=True)
        logger.info("Database and pgvector initialization successful.")
    except Exception as exc:
        logger.error("FATAL: Database initialization failed during application startup: %s", exc)
        raise RuntimeError(f"Database initialization failed during application startup: {exc}") from exc
    yield


def create_application() -> FastAPI:
    """Creates and configures the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "DARUKAA.EARTH AI Biodiversity Intelligence Chatbot API. "
            "Provides evidence-grounded, multi-variable scientific reasoning for ecological restoration."
        ),
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    application.include_router(health.router, prefix=settings.API_V1_STR)
    application.include_router(knowledge.router, prefix=settings.API_V1_STR)
    application.include_router(assessment.router, prefix=settings.API_V1_STR)
    application.include_router(chat.router, prefix=settings.API_V1_STR)
    application.include_router(scenarios.router, prefix=settings.API_V1_STR)

    @application.get("/health", tags=["Health"], include_in_schema=False)
    def health_root_alias():
        """Root health check endpoint returning service status."""
        return health.get_health()

    @application.get("/docs", include_in_schema=False)
    def docs_root_redirect():
        """Redirects root /docs to the versioned API documentation."""
        return RedirectResponse(url=f"{settings.API_V1_STR}/docs")

    @application.get("/", tags=["Root"])
    def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": "0.1.0",
            "docs": f"{settings.API_V1_STR}/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    return application


app = create_application()
