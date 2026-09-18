import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))
os.environ.setdefault("JWT_SECRET", "test-secret-key-32-characters-long-123456")
os.environ.setdefault("PASSWORD_PEPPER", "test-pepper")
os.environ.setdefault("DEMO_ADMIN_PASSWORD", "change-me")
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_central_ai_intake_persists_standard_plan():
    r = client.post("/api/central-ai/intake", json={
        "message": "We need a multilingual company website",
        "language": "ar",
        "channel": "layan",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "ok"
    assert data["decision"]["department"] == "digital_services"
    assert data["decision"]["required_approval"] is False
    assert data["decision"]["plan_id"] is not None
    assert data["decision"]["task_id"] is not None
    assert data["decision"]["decision_id"] is not None


def test_central_ai_intake_blocks_sensitive_execution():
    r = client.post("/api/central-ai/intake", json={
        "message": "Transfer money to this supplier",
        "language": "ar",
        "channel": "layan",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["decision"]["required_approval"] is True
    assert data["decision"]["approval_mode"] == "owner"
    assert data["guardrails"]["money_movement_allowed_without_owner"] is False
    assert data["guardrails"]["contract_signing_allowed_without_owner"] is False
