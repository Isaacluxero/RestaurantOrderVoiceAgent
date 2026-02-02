"""Shared test fixtures and configuration."""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "test-sid")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+1234567890")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("RESTAURANT_NAME", "Test Restaurant")

from app.main import app
from app.db.database import Base, get_db
from app.db.models import Call, Order, OrderItem
from app.core.dependencies import get_menu_repository
from app.core.config import Settings
from app.services.menu.repository import MenuRepository
from app.services.menu.in_memory_menu import InMemoryMenuProvider


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    return Settings(
        openai_api_key="test-key",
        twilio_account_sid="test-sid",
        twilio_auth_token="test-token",
        twilio_phone_number="+1234567890",
        database_url=TEST_DATABASE_URL,
        restaurant_name="Test Restaurant",
        dashboard_password="testpass123",
        session_secret_key="test-secret-key",
        tax_rate=0.0925,  # 9.25% for testing
    )


@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_db(test_db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def test_menu_path():
    """Return path to test menu YAML file."""
    return Path(__file__).parent / "fixtures" / "test_menu.yaml"


@pytest.fixture
async def test_menu_repository(test_menu_path):
    """Create menu repository with test data."""
    provider = InMemoryMenuProvider(menu_file=str(test_menu_path))
    return MenuRepository(provider)


@pytest.fixture
def override_get_db(test_db):
    """Override get_db dependency with test database."""
    async def _override_get_db():
        yield test_db
    return _override_get_db


@pytest.fixture
def override_get_menu_repository(test_menu_repository):
    """Override get_menu_repository dependency with test menu."""
    def _override_get_menu_repository():
        return test_menu_repository
    return _override_get_menu_repository


@pytest.fixture
def test_client(override_get_db, override_get_menu_repository, test_settings, monkeypatch):
    """Create FastAPI test client with overrides."""
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_menu_repository] = override_get_menu_repository

    # Override settings in modules that use it
    monkeypatch.setattr("app.core.config.settings", test_settings)
    monkeypatch.setattr("app.api.auth.settings", test_settings)

    client = TestClient(app)

    yield client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(test_client, test_settings):
    """Create test client with valid session cookie."""
    # Login with test password
    response = test_client.post(
        "/api/auth/login",
        json={"password": test_settings.dashboard_password}
    )
    assert response.status_code == 200

    # Session cookie is automatically stored in test_client
    return test_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI API client."""
    mock_client = Mock()
    mock_completion = AsyncMock()
    mock_completion.choices = [
        Mock(
            message=Mock(
                content='{"response": "Test response", "intent": "ordering", "action": {"type": "none"}}'
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    return mock_client


@pytest.fixture
def clean_auth_sessions():
    """Clean up authentication sessions before and after tests."""
    from app.api import auth
    auth._sessions.clear()
    yield
    auth._sessions.clear()


@pytest.fixture
def clean_call_sessions():
    """Clean up call sessions before and after tests."""
    from app.services.call_session import manager
    manager._sessions.clear()
    yield
    manager._sessions.clear()


@pytest.fixture(autouse=True)
def reset_menu_cache(test_menu_path):
    """Reset menu cache and restore original test menu content between tests."""
    import yaml

    # Original test menu content
    original_menu = {
        "items": [
            {
                "name": "burger",
                "description": "Classic burger",
                "price": 10.00,
                "category": "mains",
                "options": ["no onions", "extra cheese", "well done"]
            },
            {
                "name": "fries",
                "description": "Crispy fries",
                "price": 3.50,
                "category": "sides",
                "options": ["large", "small"]
            },
            {
                "name": "soda",
                "description": "Soft drink",
                "price": 2.00,
                "category": "drinks",
                "options": ["coke", "sprite", "diet"]
            }
        ]
    }

    # Restore original test menu before each test
    with open(test_menu_path, 'w') as f:
        yaml.safe_dump(original_menu, f, default_flow_style=False, sort_keys=False)

    # Clear menu cache
    from app.core.dependencies import get_menu_repository
    repo = get_menu_repository()
    repo.provider._menu = None

    yield

    # Clean up after test - restore again
    with open(test_menu_path, 'w') as f:
        yaml.safe_dump(original_menu, f, default_flow_style=False, sort_keys=False)
    repo.provider._menu = None


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test"
    )
