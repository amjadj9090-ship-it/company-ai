from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response

router = APIRouter()

REALTIME_MODEL = "gpt-realtime-2.1"
OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"

LAYAN_INSTRUCTIONS = """You are Layan, the voice AI assistant for Company AI. Speak naturally and warmly. Support the visitor's language automatically. When speaking Arabic, use Syrian/Levantine Arabic and do not use Egyptian phrasing. Keep answers clear and practical. Company AI owner approval is required before sensitive commitments such as transfers, withdrawals, signing contracts, or non-standard binding commitments. You may discuss, qualify leads, prepare quotes and drafts, but do not claim that a sensitive commitment was finalized without owner approval."""


def _realtime_session() -> dict:
    return {
        "type": "realtime",
        "model": REALTIME_MODEL,
        "audio": {
            "output": {
                "voice": "marin",
            }
        },
    }


@router.post("/api/voice-avatar/realtime-call")
async def create_layan_realtime_call(request: Request) -> Response:
    """Server-proxied WebRTC handshake for Layan."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Voice service is not configured: OPENAI_API_KEY is missing on the server.",
        )

    sdp = (await request.body()).decode("utf-8", errors="replace").strip()
    if not sdp:
        raise HTTPException(status_code=400, detail="Missing WebRTC SDP offer.")

    # OpenAI expects both SDP and session as ordinary multipart form fields.
    # Supplying a filename makes `sdp` a file upload and the Realtime endpoint
    # rejects it as a missing form field.
    files = {
        "sdp": (None, sdp),
        "session": (None, json.dumps(_realtime_session())),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Safety-Identifier": "company-ai-public",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENAI_REALTIME_CALLS_URL,
                headers=headers,
                files=files,
            )
    except httpx.HTTPError as exc:
        print(f"[LAYAN_REALTIME] provider connection error: {exc.__class__.__name__}", flush=True)
        raise HTTPException(
            status_code=502,
            detail=f"Voice provider connection failed: {exc.__class__.__name__}",
        ) from exc

    if response.status_code >= 400:
        detail = response.text[:4000]
        print(
            f"[LAYAN_REALTIME] OpenAI provider rejected call: status={response.status_code} body={detail}",
            flush=True,
        )
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Realtime provider error: HTTP {response.status_code}: {detail}",
        )

    answer_sdp = response.text.strip()
    if not answer_sdp:
        print("[LAYAN_REALTIME] provider returned empty SDP answer", flush=True)
        raise HTTPException(
            status_code=502,
            detail="Realtime provider returned an empty SDP answer.",
        )

    print("[LAYAN_REALTIME] WebRTC handshake succeeded", flush=True)
    return Response(content=answer_sdp, media_type="application/sdp")


@router.post("/api/voice-avatar/public-session")
async def create_layan_realtime_session():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Voice service is not configured yet: OPENAI_API_KEY is missing on the server.",
        )

    payload = {
        "expires_after": {"anchor": "created_at", "seconds": 600},
        "session": _realtime_session(),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Safety-Identifier": "company-ai-public",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Voice provider connection failed: {exc.__class__.__name__}",
        ) from exc

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:1000]
        raise HTTPException(
            status_code=response.status_code,
            detail={"provider_status": response.status_code, "provider_error": detail},
        )

    data = response.json()
    value = data.get("value")
    if not isinstance(value, str) or not value.startswith("ek_"):
        raise HTTPException(
            status_code=502,
            detail="Voice provider returned an invalid ephemeral client secret.",
        )

    return {
        "value": value,
        "expires_at": data.get("expires_at"),
        "session": data.get("session", {}),
        "model": REALTIME_MODEL,
    }


_original_fastapi_init = FastAPI.__init__


def _company_ai_fastapi_init(self, *args, **kwargs):
    _original_fastapi_init(self, *args, **kwargs)
    if getattr(self, "title", "") == "Company AI Global Business OS":
        self.include_router(router)


FastAPI.__init__ = _company_ai_fastapi_init
