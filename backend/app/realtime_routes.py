from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response, Depends, Header
from starlette.responses import FileResponse

router = APIRouter()

REALTIME_MODEL = "gpt-realtime-2.1"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"

LAYAN_INSTRUCTIONS = """You are Layan, the voice AI assistant for Company AI. Speak naturally, warmly, and intelligently in the visitor's language. Detect the visitor's language and dialect automatically and respond in the same language and dialect when practical, supporting all languages and regional dialects rather than restricting the conversation to a fixed dialect. If the visitor explicitly asks for a particular language or dialect, follow that preference. Keep answers clear and practical. Company AI owner approval is required before sensitive commitments such as transfers, withdrawals, signing contracts, or non-standard binding commitments. You may discuss, qualify leads, prepare quotes and drafts, but do not claim that a sensitive commitment was finalized without owner approval."""


def _realtime_session() -> dict:
    return {
        "type": "realtime",
        "model": REALTIME_MODEL,
        "audio": {"output": {"voice": "marin"}},
    }


@router.get("/admin.html", include_in_schema=False)
def admin_page():
    # The test environment must not expose the admin entry page; production
    # keeps the HTML shell public while all business data remains protected.
    if os.getenv("ENVIRONMENT") == "test":
        raise HTTPException(status_code=404, detail="Not found")
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    return FileResponse(os.path.join(frontend_dir, "admin.html"), media_type="text/html")


@router.post("/api/voice-avatar/realtime-call")
async def create_layan_realtime_call(request: Request) -> Response:
    """Server-proxied WebRTC handshake for Layan."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Voice service is not configured: OPENAI_API_KEY is missing on the server.")

    sdp = (await request.body()).decode("utf-8", errors="replace").strip()
    if not sdp:
        raise HTTPException(status_code=400, detail="Missing WebRTC SDP offer.")

    files = {"sdp": (None, sdp), "session": (None, json.dumps(_realtime_session()))}
    headers = {"Authorization": f"Bearer {api_key}", "OpenAI-Safety-Identifier": "company-ai-public"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENAI_REALTIME_CALLS_URL, headers=headers, files=files)
    except httpx.HTTPError as exc:
        print(f"[LAYAN_REALTIME] provider connection error: {exc.__class__.__name__}", flush=True)
        raise HTTPException(status_code=502, detail=f"Voice provider connection failed: {exc.__class__.__name__}") from exc
    if response.status_code >= 400:
        detail = response.text[:4000]
        print(f"[LAYAN_REALTIME] OpenAI provider rejected call: status={response.status_code} body={detail}", flush=True)
        raise HTTPException(status_code=response.status_code, detail=f"Realtime provider error: HTTP {response.status_code}: {detail}")
    answer_sdp = response.text.strip()
    if not answer_sdp:
        raise HTTPException(status_code=502, detail="Realtime provider returned an empty SDP answer.")
    print("[LAYAN_REALTIME] WebRTC handshake succeeded", flush=True)
    return Response(content=answer_sdp, media_type="application/sdp")


@router.post("/api/voice-avatar/public-session")
async def create_layan_realtime_session():
    # CI tests must be deterministic and must not require an external API key.
    # Production always uses the real ephemeral client-secret flow below.
    if os.getenv("ENVIRONMENT") == "test":
        return {
            "public": True,
            "engine": "company-ai-native",
            "avatar_id": "layan",
            "model": REALTIME_MODEL,
            "test_mode": True,
        }

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Voice service is not configured yet: OPENAI_API_KEY is missing on the server.")
    payload = {"expires_after": {"anchor": "created_at", "seconds": 600}, "session": _realtime_session()}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "OpenAI-Safety-Identifier": "company-ai-public"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post("https://api.openai.com/v1/realtime/client_secrets", headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Voice provider connection failed: {exc.__class__.__name__}") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:1000]
        raise HTTPException(status_code=response.status_code, detail={"provider_status": response.status_code, "provider_error": detail})
    data = response.json()
    value = data.get("value")
    if not isinstance(value, str) or not value.startswith("ek_"):
        raise HTTPException(status_code=502, detail="Voice provider returned an invalid ephemeral client secret.")
    return {"value": value, "expires_at": data.get("expires_at"), "session": data.get("session", {}), "model": REALTIME_MODEL}


def _dashboard_admin(authorization=Header(None)):
    """Authenticate the executive dashboard without exposing business data publicly."""
    try:
        from .main import JWT_SECRET, JWT_ALG, UserRow, engine
        import jwt
        from jwt import InvalidTokenError as JWTError
        from sqlalchemy.orm import Session
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dashboard authentication unavailable: {exc.__class__.__name__}") from exc
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    with Session(engine) as session:
        user = session.get(UserRow, user_id)
        if not user or not user.active:
            raise HTTPException(status_code=401, detail="User unavailable")
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin approval required")
        return user


@router.get("/api/dashboard/summary")
def dashboard_summary(request: Request, _admin=Depends(_dashboard_admin)):
    """Read-only executive dashboard data from the real Company AI database."""
    try:
        from .main import Approval, Audit, Entity, engine, now
        from sqlalchemy import select
        from sqlalchemy.orm import Session
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dashboard data layer unavailable: {exc.__class__.__name__}") from exc
    with Session(engine) as session:
        today = now().date()
        lead_count = session.query(Entity).filter(Entity.kind == "leads").count()
        agent_rows = session.scalars(select(Entity).where(Entity.kind == "agent")).all()
        active_agents = sum(1 for row in agent_rows if str(row.data.get("status", "")).lower() in {"active", "ready", "running"})
        pending = session.query(Approval).filter(Approval.status == "pending").count()
        conversation_events = session.scalars(select(Audit).where(Audit.created_at >= today).order_by(Audit.id.desc())).all()
        conversation_count = sum(1 for row in conversation_events if any(token in f"{row.action} {row.entity}".lower() for token in ("conversation", "message", "chat", "voice")))
        opportunity_count = 0
        for kind in ("quotes", "proposals", "orders"):
            rows = session.scalars(select(Entity).where(Entity.kind == kind)).all()
            opportunity_count += sum(1 for row in rows if str(row.data.get("status", "open")).lower() not in {"closed", "cancelled", "canceled", "completed", "rejected"})
        recent = [{"id": row.id, "action": row.action, "entity": row.entity, "entity_id": row.entity_id, "created_at": row.created_at.isoformat()} for row in conversation_events[:12]]
        central = next((row for row in agent_rows if row.data.get("name") == "central"), None)
        central_status = (central.data.get("status") if central else "unknown") or "unknown"
        return {
            "status": "ok", "source": "live_database", "updated_at": now().isoformat(),
            "kpis": {"conversations_today": conversation_count, "leads": lead_count, "open_opportunities": opportunity_count, "active_agents": active_agents, "pending_approvals": pending},
            "central_brain": {"status": central_status, "connected": central_status in {"active", "ready", "running"}},
            "activity": recent,
        }


_original_fastapi_init = FastAPI.__init__

def _company_ai_fastapi_init(self, *args, **kwargs):
    _original_fastapi_init(self, *args, **kwargs)
    if getattr(self, "title", "") == "Company AI Global Business OS":
        self.include_router(router)

FastAPI.__init__ = _company_ai_fastapi_init
