"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.logging import setup_logging
from app.db.database import init_db
from app.api import health, webhooks, orders, menu


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

# Include routers (must be before static file mounting to take precedence)
app.include_router(health.router, tags=["health"])
app.include_router(webhooks.voice.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(orders.router, tags=["orders"])
app.include_router(menu.router, tags=["menu"])

# Mount static files (for frontend)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Mount assets directory at /assets path
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
async def root():
    """Serve frontend index.html."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "AI Voice Agent API",
        "version": "0.1.0",
        "frontend": "Frontend not built. Run 'npm run build' in the frontend directory.",
    }

