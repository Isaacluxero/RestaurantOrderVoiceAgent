"""Main FastAPI application."""
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from contextlib import asynccontextmanager
import os

from app.core.logging import setup_logging
from app.db.database import init_db
from app.api import health, webhooks, orders, menu, auth


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
app.include_router(auth.router, tags=["auth"])  # Auth endpoints (no protection needed)
app.include_router(health.router, tags=["health"])  # Health check (no protection needed)
app.include_router(webhooks.voice.router, prefix="/webhooks", tags=["webhooks"])  # Twilio webhooks (no protection needed)
app.include_router(orders.router, tags=["orders"], dependencies=[Depends(auth.require_auth)])  # Protected
app.include_router(menu.router, tags=["menu"], dependencies=[Depends(auth.require_auth)])  # Protected

# Mount static files (for frontend)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Mount assets directory at /assets path
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
async def root(request: Request):
    """Serve frontend index.html (authentication handled client-side)."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "AI Voice Agent API",
        "version": "0.1.0",
        "frontend": "Frontend not built. Run 'npm run build' in the frontend directory.",
    }


@app.get("/login")
async def login_page():
    """Serve login page (unprotected)."""
    # For now, the React app will handle routing to login
    # But we need this route to be accessible
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Login page not available. Build frontend first."}

