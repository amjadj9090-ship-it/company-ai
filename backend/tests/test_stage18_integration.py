import os
import tempfile
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///" + tempfile.mktemp(suffix=".db"))
os.environ.setdefault("JWT_SECRET", "test-secret-key-32-characters-long-123456")
os.environ.setdefault("PASSWORD_PEPPER", "test-pepper")
os.environ.setdefault("DEMO_ADMIN_PASSWORD", "change-me")
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient
from app.main import Entity, Session, app, engine

client = TestClient(app)


def login_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "change-me"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_stage18_public_sales_to_crm_to_brain_contract():
    sales_cfg = client.get("/api/sales-agent/public/config")
    assert sales_cfg.status_code == 200, sales_cfg.text
    build_id = sales_cfg.json()["build_id"]

    conversation = client.post(
        f"/api/sales-agent/{build_id}/conversation",
        json={"message": "I need a company website", "language": "en"},
    )
    assert conversation.status_code == 200, conversation.text
    assert conversation.json()["status"] == "ok"
    assert conversation.json()["recommendations"]

    lead = client.post(
        "/api/crm/leads",
        json={
            "name": "Stage 18 Customer",
            "email": "stage18@example.com",
            "company": "Stage 18 Co",
            "service": "website",
            "value": 500,
        },
    )
    assert lead.status_code == 200, lead.text
    lead_id = lead.json()["id"]

    qualified = client.patch(
        f"/api/crm/leads/{lead_id}",
        json={"stage": "qualified"},
    )
    assert qualified.status_code == 200, qualified.text
    assert qualified.json()["stage"] == "qualified"

    brain = client.post(
        "/api/brain/plan",
        json={
            "message": "Prepare a standard website service proposal",
            "language": "en",
            "channel": "website",
            "context": {"lead_id": lead_id},
        },
    )
    assert brain.status_code == 200, brain.text
    decision = brain.json()["decision"]
    assert decision["department"] == "digital_services"
    assert decision["approval_mode"] == "auto_standard"
    assert decision["required_approval"] is False


def test_stage18_proposal_token_view_accept_order_end_to_end():
    headers = login_headers()
    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        lead = Entity(
            kind="leads",
            data={"name": "Stage 18 Lifecycle", "email": "lifecycle18@example.com"},
            created_at=now,
            updated_at=now,
        )
        db.add(lead)
        db.flush()
        proposal = Entity(
            kind="proposals",
            data={
                "lead_id": lead.id,
                "title": "Stage 18 Website",
                "scope": ["website"],
                "status": "sent",
                "human_approval_required": False,
            },
            created_at=now,
            updated_at=now,
        )
        db.add(proposal)
        db.commit()
        proposal_id = proposal.id

    token_response = client.post(
        "/api/public-lifecycle/proposal/token",
        params={"proposal_id": proposal_id},
        headers=headers,
    )
    assert token_response.status_code == 200, token_response.text
    token = token_response.json()["token"]

    viewed = client.post(
        "/api/public-lifecycle/proposal/view",
        json={"token": token},
    )
    assert viewed.status_code == 200, viewed.text
    assert viewed.json()["id"] == proposal_id
    assert viewed.json()["status"] == "sent"

    accepted = client.post(
        "/api/public-lifecycle/proposal/accept",
        json={"token": token, "customer_note": "Approved for implementation"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted_by_customer"

    order = client.post(
        "/api/public-lifecycle/proposal/order",
        json={"token": token},
    )
    assert order.status_code == 200, order.text
    order_data = order.json()
    assert order_data["proposal_id"] == proposal_id
    assert order_data["status"] == "confirmed"
    assert order_data["payment_status"] == "unpaid"
    assert order_data["execution_locked"] is False

    reused = client.post(
        "/api/public-lifecycle/proposal/order",
        json={"token": token},
    )
    assert reused.status_code == 404


def test_stage18_sensitive_boundary_survives_brain_and_finance_layers():
    brain = client.post(
        "/api/brain/plan",
        json={"message": "transfer company money to a bank", "language": "en"},
    )
    assert brain.status_code == 200, brain.text
    decision = brain.json()["decision"]
    assert decision["department"] == "finance_legal"
    assert decision["approval_mode"] == "owner"
    assert decision["required_approval"] is True

    headers = login_headers()
    transaction = client.post(
        "/api/finance/transactions",
        headers=headers,
        json={
            "transaction_type": "bank_withdrawal",
            "amount": 100,
            "description": "Stage 18 boundary test",
        },
    )
    assert transaction.status_code == 200, transaction.text
    assert transaction.json()["approval_required"] is True
    assert transaction.json()["executed"] is False


def test_stage18_frontend_backend_voice_and_lifecycle_wiring_remains_connected():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    index = open(os.path.join(root, "frontend", "index.html"), encoding="utf-8").read()
    realtime = open(
        os.path.join(root, "frontend", "layan-realtime-hotfix.js"), encoding="utf-8"
    ).read()

    assert "layan-realtime-hotfix.js" in index
    assert "voiceChoice" in index
    assert "startLayanVoice" in realtime
    assert "getUserMedia" in realtime
    assert "/api/voice-avatar/realtime-call" in realtime
    assert "/api/voice-avatar/public-session" in index or "/api/voice-avatar/public-session" in realtime

    paths = {route.path for route in app.routes}
    for path in (
        "/api/brain/plan",
        "/api/crm/leads",
        "/api/public-lifecycle/proposal/view",
        "/api/public-lifecycle/proposal/accept",
        "/api/public-lifecycle/proposal/order",
        "/api/voice-avatar/realtime-call",
    ):
        assert path in paths, path
