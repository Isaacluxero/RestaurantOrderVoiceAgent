"""Health check endpoint."""
import logging
from fastapi import APIRouter, Request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    logger.debug(
        f"[HEALTH] Health check requested - Client: {request.client.host if request.client else 'unknown'}"
    )
    return {"status": "healthy"}

