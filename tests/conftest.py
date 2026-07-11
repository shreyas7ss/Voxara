import pytest

from app.services.db import create_all


@pytest.fixture(scope="session", autouse=True)
def _ensure_listings_schema():
    create_all()
