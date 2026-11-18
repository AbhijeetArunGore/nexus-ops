"""
Pytest session configuration and fixtures for NEXUS Ops.
Guarantees a clean, isolated SQLite test database with all tables created,
preventing 'no such table: incidents' errors on fresh clones.
"""
import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def test_db_engine():
    """Create an isolated temporary SQLite database for the test session."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_nexus_ops.db")
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )
    # Create all tables explicitly
    Base.metadata.create_all(bind=engine)
    yield engine
    # Teardown
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """Provide a transactional database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(test_db_engine):
    """
    TestClient context manager with dependency override for get_db.
    Guarantees that tables exist and lifespan is triggered.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
