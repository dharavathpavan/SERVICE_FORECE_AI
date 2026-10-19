import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def org_factory(db_session):
    """Creates an Organization directly in the test session."""
    import uuid

    from app.models.tenant import Organization

    def _make(name: str = "Test Org", monthly_call_limit: int = 500):
        org = Organization(
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
            is_active=True,
            monthly_call_limit=monthly_call_limit,
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)
        return org

    return _make
