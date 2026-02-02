"""Authentication endpoints and utilities."""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import secrets
import hashlib
from datetime import datetime, timedelta

from app.core.config import settings

router = APIRouter()

# In-memory session storage (use Redis in production)
_sessions: dict[str, dict] = {}


class LoginRequest(BaseModel):
    """Login request model."""
    password: str


class SessionInfo(BaseModel):
    """Session information response."""
    authenticated: bool
    expires_at: Optional[str] = None


def create_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """Hash password for comparison."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_session(response: Response) -> str:
    """Create a new session and set cookie."""
    session_token = create_session_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)

    _sessions[session_token] = {
        "authenticated": True,
        "expires_at": expires_at,
        "created_at": datetime.utcnow()
    }

    # Set HTTP-only cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )

    return session_token


def get_session_token(request: Request) -> Optional[str]:
    """Extract session token from cookie."""
    return request.cookies.get("session_token")


def verify_session(session_token: Optional[str]) -> bool:
    """Verify if session token is valid and not expired."""
    if not session_token:
        return False

    session = _sessions.get(session_token)
    if not session:
        return False

    # Check expiration
    if datetime.utcnow() > session["expires_at"]:
        del _sessions[session_token]
        return False

    return session.get("authenticated", False)


async def require_auth(request: Request) -> bool:
    """Dependency to require authentication."""
    session_token = get_session_token(request)
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True


@router.post("/api/auth/login")
async def login(login_req: LoginRequest, response: Response):
    """Login endpoint."""
    # Verify password
    if login_req.password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Create session
    session_token = create_session(response)

    return {
        "success": True,
        "message": "Login successful",
        "expires_at": _sessions[session_token]["expires_at"].isoformat()
    }


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """Logout endpoint."""
    session_token = get_session_token(request)
    if session_token and session_token in _sessions:
        del _sessions[session_token]

    # Clear cookie
    response.delete_cookie("session_token")

    return {"success": True, "message": "Logged out"}


@router.get("/api/auth/session")
async def get_session_info(request: Request) -> SessionInfo:
    """Get current session information."""
    session_token = get_session_token(request)

    if verify_session(session_token):
        session = _sessions[session_token]
        return SessionInfo(
            authenticated=True,
            expires_at=session["expires_at"].isoformat()
        )

    return SessionInfo(authenticated=False)
