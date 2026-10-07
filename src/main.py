"""Main entry point for the FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router as api_router
from src.core.config import settings
from src.core.logging import logger, setup_logging
from src.core.sentry import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown hooks."""
    setup_logging()
    init_sentry()
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    yield
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Automated triage and review-queue assistant for customer support inboxes.",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Mount frontend directory for static assets and HTML UI
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

    @app.get("/ui", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    async def serve_ui():
        """Serve the Human-in-the-Loop review queue frontend."""
        return FileResponse(str(frontend_dir / "index.html"))


@app.get("/", tags=["root"])
async def root():
    """Root info endpoint."""
    return {
        "app": settings.app_name,
        "status": "online",
        "docs_url": "/docs",
        "ui_url": "/ui",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
