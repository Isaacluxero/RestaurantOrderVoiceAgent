"""Unit tests for authentication system."""
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.api import auth


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password(self):
        """Test that password is hashed correctly with SHA256."""
        password = "testpassword123"
        hashed = auth.hash_password(password)

        # SHA256 produces 64 character hex string
        assert len(hashed) == 64
        assert isinstance(hashed, str)

    def test_same_password_same_hash(self):
        """Test that same password produces same hash."""
        password = "testpassword123"
        hash1 = auth.hash_password(password)
        hash2 = auth.hash_password(password)

        assert hash1 == hash2

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"

        hash1 = auth.hash_password(password1)
        hash2 = auth.hash_password(password2)

        assert hash1 != hash2


class TestSessionToken:
    """Test session token generation."""

    def test_create_session_token(self):
        """Test that session token is generated correctly."""
        token = auth.create_session_token()

        # token_urlsafe(32) generates ~43 character URL-safe base64 string
        assert len(token) >= 40
        assert isinstance(token, str)
        # Should be URL-safe characters
        import string
        url_safe_chars = string.ascii_letters + string.digits + '-_'
        assert all(c in url_safe_chars for c in token)

    def test_unique_tokens(self):
        """Test that each call generates unique token."""
        token1 = auth.create_session_token()
        token2 = auth.create_session_token()
        token3 = auth.create_session_token()

        assert token1 != token2
        assert token2 != token3
        assert token1 != token3


class TestSessionManagement:
    """Test session creation and verification."""

    def test_create_session(self, clean_auth_sessions):
        """Test that session is created with correct structure."""
        from unittest.mock import Mock
        from fastapi import Response

        # Create mock response
        response = Mock(spec=Response)
        response.set_cookie = Mock()

        token = auth.create_session(response)

        # Verify token format
        assert len(token) >= 40

        # Verify session stored in _sessions
        assert token in auth._sessions

        session = auth._sessions[token]
        assert session["authenticated"] is True
        assert "expires_at" in session
        assert "created_at" in session

        # Verify expiration is ~24 hours from now
        expires_at = session["expires_at"]
        now = datetime.utcnow()
        time_diff = expires_at - now

        # Should be close to 24 hours (within 1 minute tolerance)
        assert timedelta(hours=23, minutes=59) < time_diff < timedelta(hours=24, minutes=1)

    def test_verify_session_valid(self, clean_auth_sessions):
        """Test that valid session is verified correctly."""
        from unittest.mock import Mock
        from fastapi import Response

        response = Mock(spec=Response)
        response.set_cookie = Mock()

        token = auth.create_session(response)

        # Should return True for valid session
        assert auth.verify_session(token) is True

    def test_verify_session_invalid_token(self, clean_auth_sessions):
        """Test that invalid token returns False."""
        # Non-existent token
        assert auth.verify_session("invalid_token_12345") is False

        # None token
        assert auth.verify_session(None) is False

    def test_verify_session_expired(self, clean_auth_sessions):
        """Test that expired session returns False and is cleaned up."""
        from unittest.mock import Mock
        from fastapi import Response

        response = Mock(spec=Response)
        response.set_cookie = Mock()

        token = auth.create_session(response)

        # Manually set expiration to past
        expired_time = datetime.utcnow() - timedelta(hours=1)
        auth._sessions[token]["expires_at"] = expired_time

        # Should return False
        assert auth.verify_session(token) is False

        # Session should be removed from _sessions
        assert token not in auth._sessions


class TestAuthAPIEndpoints:
    """Test authentication API endpoints."""

    def test_login_success(self, test_client, test_settings, clean_auth_sessions):
        """Test successful login with correct password."""
        response = test_client.post(
            "/api/auth/login",
            json={"password": test_settings.dashboard_password}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"

        # Verify session cookie is set
        assert "session_token" in response.cookies

        # Verify session stored
        token = response.cookies["session_token"]
        assert token in auth._sessions

    def test_login_failure(self, test_client, clean_auth_sessions):
        """Test login failure with wrong password."""
        response = test_client.post(
            "/api/auth/login",
            json={"password": "wrongpassword"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid password"

        # Verify no session created
        assert len(auth._sessions) == 0

    def test_logout(self, authenticated_client):
        """Test logout clears session."""
        # Logout
        response = authenticated_client.post("/api/auth/logout")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Logged out"

        # Verify cookie is cleared (max_age=-1 or max-age=0)
        set_cookie = response.headers.get("set-cookie", "")
        assert "max-age=0" in set_cookie.lower() or "max_age=0" in set_cookie.lower()

    def test_get_session_status_authenticated(self, authenticated_client):
        """Test session status endpoint with valid session."""
        response = authenticated_client.get("/api/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert "expires_at" in data

    def test_get_session_status_unauthenticated(self, test_client):
        """Test session status endpoint without session."""
        response = test_client.get("/api/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestRequireAuthDependency:
    """Test require_auth FastAPI dependency."""

    def test_require_auth_authenticated(self, authenticated_client):
        """Test that authenticated requests are allowed."""
        # Try accessing protected endpoint
        response = authenticated_client.get("/api/menu")

        # Should succeed (menu endpoint uses require_auth for some operations)
        assert response.status_code == 200

    def test_require_auth_unauthenticated(self, test_client):
        """Test that unauthenticated requests are blocked."""
        # Try accessing protected endpoint without auth
        response = test_client.get("/api/orders/history")

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication required"
