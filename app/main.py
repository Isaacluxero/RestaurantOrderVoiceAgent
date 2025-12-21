"""Main FastAPI application."""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.logging import setup_logging
from app.db.database import init_db
from app.api import health, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="AI Voice Agent",
    description="AI Voice Agent for Restaurant Order Taking",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(webhooks.voice.router, prefix="/webhooks", tags=["webhooks"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Voice Agent API",
        "version": "0.1.0",
    }

