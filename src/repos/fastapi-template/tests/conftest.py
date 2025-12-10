"""
Pytest configuration for Aspect Code benchmark tests.

This conftest sets up an in-memory SQLite database for testing,
allowing tests to run without Docker or PostgreSQL.

PERFORMANCE: Uses fast password hashing for tests instead of bcrypt.
"""

import sys
import os
from pathlib import Path

# Add the target repo's backend to the path
# conftest.py is at: src/repos/fastapi-template/tests/conftest.py
# Target repo is cloned at: repos/fastapi-template/
TESTS_DIR = Path(__file__).parent  # src/repos/fastapi-template/tests/
REPOS_DIR = TESTS_DIR.parent.parent  # src/repos/
HARNESS_DIR = REPOS_DIR.parent  # src/
PROJECT_ROOT = HARNESS_DIR.parent  # Project root
FASTAPI_TEMPLATE_ROOT = PROJECT_ROOT / "repos" / "fastapi-template"  # repos/fastapi-template/
BACKEND_PATH = FASTAPI_TEMPLATE_ROOT / "backend"
TESTS_PATH = BACKEND_PATH / "tests"

# Add backend to path so we can import from app
sys.path.insert(0, str(BACKEND_PATH))
# Add tests to path so tests.utils can be found
sys.path.insert(0, str(TESTS_PATH.parent))

# Set environment variables for testing BEFORE importing settings
os.environ.setdefault("PROJECT_NAME", "Aspect Code Benchmark")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("FIRST_SUPERUSER", "admin@example.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "testpassword123")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-benchmarks")

# PERFORMANCE FIX: Patch passlib to use a fast hashing scheme for tests
# bcrypt is intentionally slow (~200ms per hash), which makes tests slow
from passlib.context import CryptContext

# Create a fast password context for testing (uses plaintext with prefix)
_fast_pwd_context = CryptContext(schemes=["plaintext"], deprecated="auto")

# Patch the security module before it's imported
import app.core.security as security_module
security_module.pwd_context = _fast_pwd_context

# SQLITE FIX: Patch get_current_user to handle UUID string conversion
# SQLite stores UUIDs as strings, but the app expects UUID objects
import app.api.deps as deps_module
import jwt
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

_original_get_current_user = deps_module.get_current_user

def _patched_get_current_user(session, token):
    """Patched version that converts string UUID to UUID object for SQLite."""
    from app.models import TokenPayload, User
    from app.core.config import settings
    from app.core import security
    import uuid as uuid_mod
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # Convert string UUID to UUID object for SQLite compatibility
    user_id = token_data.sub
    if isinstance(user_id, str):
        user_id = uuid_mod.UUID(user_id)
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

deps_module.get_current_user = _patched_get_current_user

# Now we can import from the fastapi template
from collections.abc import Generator
import uuid as uuid_module

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.main import app
from app.models import Item, User


# Use SQLite in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Register SQLite adapter for UUID type
import sqlite3

# Register UUID to string converter for SQLite
sqlite3.register_adapter(uuid_module.UUID, lambda u: str(u))
# Register string to UUID converter when reading from SQLite
sqlite3.register_converter("UUID", lambda b: uuid_module.UUID(b.decode()))

# SQLITE FIX: Patch SQLAlchemy's UUID type to handle string inputs
# This is needed because session.get(User, "uuid-string") fails with PostgreSQL UUID type
from sqlalchemy.sql import sqltypes

_original_uuid_bind_processor = sqltypes.Uuid.bind_processor

def _patched_uuid_bind_processor(self, dialect):
    """Patched bind_processor that handles both UUID and string inputs."""
    original_processor = _original_uuid_bind_processor(self, dialect)
    
    def process(value):
        if value is None:
            return value
        # Convert string to UUID first if needed
        if isinstance(value, str):
            value = uuid_module.UUID(value)
        # Then run the original processor
        if original_processor is not None:
            return original_processor(value)
        return value
    
    return process

sqltypes.Uuid.bind_processor = _patched_uuid_bind_processor

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    },
    poolclass=StaticPool,
)


# Handle UUID type for SQLite by storing as strings
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_test_db():
    """Create all tables and the superuser."""
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create superuser if it doesn't exist
        from sqlmodel import select
        
        user = session.exec(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        ).first()
        
        if not user:
            # Use the fast hashing (plaintext with prefix)
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=_fast_pwd_context.hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
                full_name="Test Admin",
            )
            session.add(user)
            session.commit()


# Patch the app's database dependency to use our test engine
from app.api.deps import get_db as original_get_db


def get_test_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# Override the dependency
app.dependency_overrides[original_get_db] = get_test_db

# SQLITE FIX: Override get_current_user to handle UUID string conversion
# SQLite stores UUIDs as strings, but session.get(User, str_uuid) fails with PostgreSQL's UUID type
def _sqlite_get_current_user(session: Session, token: str) -> User:
    """SQLite-compatible version of get_current_user that handles UUID string conversion."""
    from app.models import TokenPayload, User
    from app.core.config import settings
    from app.core import security
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # Convert string UUID to UUID object for SQLite compatibility
    user_id = token_data.sub
    if isinstance(user_id, str):
        user_id = uuid_module.UUID(user_id)
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# Override the get_current_user dependency
from app.api.deps import get_current_user as original_get_current_user
app.dependency_overrides[original_get_current_user] = _sqlite_get_current_user


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Initialize the test database once per session."""
    init_test_db()
    yield
    # Cleanup after all tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def db() -> Generator[Session, None, None]:
    """Get a database session for tests."""
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers for the superuser."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    response = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    """Get auth headers for a normal user."""
    from sqlmodel import select
    
    # Create or get normal user
    email = settings.EMAIL_TEST_USER
    password = "testpassword"
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            user = User(
                email=email,
                hashed_password=_fast_pwd_context.hash(password),
                is_superuser=False,
                is_active=True,
                full_name="Test User",
            )
            session.add(user)
            session.commit()
    
    login_data = {"username": email, "password": password}
    response = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "aspect_bench: mark test as part of Aspect Code benchmark suite"
    )
    config.addinivalue_line(
        "markers", "regression: mark test as a regression test to detect side effects"
    )
