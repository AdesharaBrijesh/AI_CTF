import os

os.environ["LLM_MODE"] = "mock"
os.environ["RATE_LIMIT_PER_MIN"] = "1000"
os.environ["DYNAMIC_FLAGS"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
for k in [k for k in os.environ if k.startswith("FLAG_L")]:
    del os.environ[k]

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_FLAGS
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def flags():
    return DEFAULT_FLAGS
