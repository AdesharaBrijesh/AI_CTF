import os

os.environ["LLM_MODE"] = "mock"
os.environ["RATE_LIMIT_PER_MIN"] = "1000"
os.environ["DYNAMIC_FLAGS"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
for n in range(1, 11):
    os.environ[f"FLAG_L{n}"] = f"FLAG{{test_flag_{n}}}"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


