import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import Setting, Job, JobLog # Import all models to register on Base

# In-memory database with StaticPool for thread-safe access
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(name="db_session")
def db_session_fixture():
    engine = create_engine(
        TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Patch SessionLocal globally for background tasks
    import backend.app.database
    original_session_local = backend.app.database.SessionLocal
    backend.app.database.SessionLocal = TestingSessionLocal

    # Initialize default settings record
    db = TestingSessionLocal()
    default_setting = Setting(
        provider="mock",
        api_key="sk-proj-testkey1234",
        base_url="http://localhost:8000/v1",
        model="mock-model",
        temperature=0.2,
        max_output_tokens=4000,
        chunk_size=10000,
        max_repo_size_mb=100,
        max_file_size_kb=200,
        github_token="ghp_token1234567890",
        output_dir="docs/outputs",
        keep_cloned_repos=False
    )
    db.add(default_setting)
    db.commit()
    
    yield db
    
    db.close()
    backend.app.database.SessionLocal = original_session_local
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
