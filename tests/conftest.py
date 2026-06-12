import pytest

from notification_rake.config import Settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("GOTIFY_TOKEN", "test-token")
    return Settings()
