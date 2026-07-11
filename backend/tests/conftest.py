import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LLM_PROVIDER"] = "none"
os.environ["WEATHER_PROVIDER"] = "local"
os.environ["RAG_ENABLED"] = "false"

from app.config import get_settings

get_settings.cache_clear()

import app.database.session as session_mod
from app.database import base  # noqa: F401 — registers all models with Base.metadata
from app.database.session import Base, get_db
from app.models import User
from app.services.security import hash_password


@pytest.fixture(scope="session")
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture(scope="session")
def sample_image(tmp_dir):
    from PIL import Image

    img = Image.new("RGB", (224, 224), color=(34, 139, 34))
    path = tmp_dir / "test_leaf.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def sample_image_bytes(sample_image):
    return sample_image.read_bytes()


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def db_user(db_session):
    user = User(
        email="test@example.com",
        name="Test User",
        language="en",
        hashed_password=hash_password("TestPass123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(db_user):
    from app.services.security import create_access_token

    token = create_access_token(db_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def mock_onnx_session():
    import numpy as np

    mock = MagicMock()
    input_mock = MagicMock()
    input_mock.name = "input"
    mock.get_inputs.return_value = [input_mock]
    logits = np.zeros((1, 10), dtype=np.float32)
    logits[0, 0] = 5.0
    mock.run.return_value = [logits]
    return mock


@pytest.fixture()
def client(db_engine):
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    original_engine = session_mod.engine
    original_SessionLocal = session_mod.SessionLocal
    session_mod.engine = db_engine
    session_mod.SessionLocal = TestSession

    from app.main import app

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc

    app.dependency_overrides.clear()
    session_mod.engine = original_engine
    session_mod.SessionLocal = original_SessionLocal


@pytest.fixture()
def mock_llm_provider():
    mock = MagicMock()
    mock.is_available = True
    mock.provider_name = "mock"
    mock.complete.return_value = "This is a mock LLM response about your crop disease."
    return mock
