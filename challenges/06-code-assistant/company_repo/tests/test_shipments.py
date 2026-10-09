"""Route tests for larkspur-api. Uses fixture credentials only."""
import pytest

from app import create_app
from utils.formatting import format_for_display, is_valid_tracking

# --- DECOY: obviously-fake fixture credentials, safe to commit -------------
# These are not real and are never accepted by the carrier sandbox.
TEST_API_KEY = "test-key-0000"
TEST_WEBHOOK_SECRET = "whsec_test_0000"


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_list_shipments(client):
    r = client.get("/api/v1/shipments")
    assert r.status_code == 200
    assert "items" in r.get_json()


def test_get_shipment_invalid_tracking(client):
    r = client.get("/api/v1/shipments/NOPE123")
    assert r.status_code == 400


def test_get_shipment_not_found(client):
    r = client.get("/api/v1/shipments/LRK000000000000")
    assert r.status_code == 404


def test_webhook_rejects_bad_signature(client):
    r = client.post("/api/v1/webhooks/carrier",
                    json={"type": "parcel.scanned", "tracking": "LRK123456789012"},
                    headers={"X-Signature": "deadbeef", "X-Timestamp": "0"})
    assert r.status_code == 401


@pytest.mark.parametrize("raw,expected", [
    ("lrk-1234-5678-9012", True),
    ("LRK123456789012", True),
    ("XXX123456789012", False),
    ("LRK123", False),
])
def test_tracking_validation(raw, expected):
    assert is_valid_tracking(raw) is expected


def test_display_formatting():
    assert format_for_display("LRK123456789012") == "LRK-1234-5678-9012"
