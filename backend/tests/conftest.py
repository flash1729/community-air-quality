import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("OPENAQ_API_KEY", "")
    get_settings.cache_clear()
    from app.main import create_app

    application = create_app()
    with TestClient(application) as client:
        yield client, application
    get_settings.cache_clear()
