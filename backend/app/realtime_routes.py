from __future__ import annotations

import json
import logging
import os

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response, Depends, Header
from starlette.responses import FileResponse

router = APIRouter()
from .central_brain import router as central_ai_router
router.include_router(central_ai_router)
LOGGER = logging.getLogger("company_ai.realtime")

REALTIME_MODEL = "gpt-realtime-2.1"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
OPENAI_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"

LAYAN_INSTRUCTIONS = """You are Layan, the voice AI assistant for Company AI. Speak naturally, warmly, and intelligently in the visitor's language. Detect the visitor's language and dialect automatically and respond in the same language and dialect when practical, supporting all languages and regional dialects rather than restricting the conversation to a fixed dialect. Arabic dialects including Syrian/Levantine Arabic and Egyptian Arabic are supported, as are other regional dialects. If the visitor explicitly asks for a particular language or dialect, follow that preference. Keep answers clear and practical. Company AI owner approval is required before sensitive commitments such as transfers, withdrawals, signing contracts, or non-standard binding commitments. You may discuss, qualify leads, prepare quotes and drafts, but do not claim that a sensitive commitment was finalized without owner approval."""


def _realtime_session() -> dict:
    return {
        "type": "realtime",
        "model": REALTIME_MODEL,
        "audio": {"output": {"voice": "marin"}},
        "instructions": LAYAN_INSTRUCTIONS,
    }


def _provider_headers(api_key: str, *, json_content: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Safety-Identifier": "company-ai-public",
    }
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def _provider_error(exc: httpx.HTTPError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Voice provider connection failed: {exc.__class__.__name__}")


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

    boundary = "company-ai-realtime-call-boundary"
    session_json = json.dumps(_realtime_session(), separators=(",", ":"))
    multipart_body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="sdp"\r\n'
        "Content-Type: application/sdp\r\n\r\n"
        f"{sdp}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="session"\r\n'
        "Content-Type: application/json\r\n\r\n"
        f"{session_json}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENAI_REALTIME_CALLS_URL,
                headers={
                    **_provider_headers(api_key),
                    "Accept": "application/sdp",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                content=multipart_body,
            )
    except httpx.HTTPError as exc:
        LOGGER.warning("Layan realtime provider connection failed: %s", exc.__class__.__name__)
        raise _provider_error(exc) from exc
    if response.status_code >= 400:
        detail = response.text[:4000]
        LOGGER.warning("Layan realtime provider rejected call: status=%s body=%s", response.status_code, detail)
        raise HTTPException(status_code=response.status_code, detail=f"Realtime provider error: HTTP {response.status_code}: {detail}")
    answer_sdp = response.text.strip()
    if not answer_sdp:
        raise HTTPException(status_code=502, detail="Realtime provider returned an empty SDP answer.")
    LOGGER.info("Layan WebRTC handshake succeeded")
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
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                OPENAI_CLIENT_SECRETS_URL,
                headers=_provider_headers(api_key, json_content=True),
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise _provider_error(exc) from exc
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
