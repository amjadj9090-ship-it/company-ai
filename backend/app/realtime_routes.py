from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, FastAPI, HTTPException

router = APIRouter()

REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-realtime-2.1")

LAYAN_INSTRUCTIONS = """You are Layan, the voice AI assistant for Company AI. Speak naturally and warmly. Support the visitor's language automatically. When speaking Arabic, use Syrian/Levantine Arabic and do not use Egyptian phrasing. Keep answers clear and practical. Company AI owner approval is required before sensitive commitments such as transfers, withdrawals, signing contracts, or non-standard binding commitments. You may discuss, qualify leads, prepare quotes and drafts, but do not claim that a sensitive commitment was finalized without owner approval."""


@router.post("/api/voice-avatar/public-session")
async def create_layan_realtime_session():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Voice service is not configured yet: OPENAI_API_KEY is missing on the server.")

    payload = {
        "expires_after": {"anchor": "created_at", "seconds": 600},
        "session": {
            "type": "realtime",
            "model": REALTIME_MODEL,
            "instructions": LAYAN_INSTRUCTIONS,
            "audio": {
                "input": {
                    "turn_detection": {
                        "type": "semantic_vad",
                        "create_response": True,
                        "interrupt_response": True,
                    },
                    "transcription": {
                        "model": "gpt-4o-transcribe",
                    },
                },
                "output": {
                    "voice": "marin",
                },
            },
            "output_modalities": ["audio"],
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Voice provider connection failed: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:500]
        raise HTTPException(status_code=502, detail={"provider_status": response.status_code, "provider_error": detail})

    data = response.json()
    value = data.get("value")
    if not isinstance(value, str) or not value.startswith("ek_"):
        raise HTTPException(status_code=502, detail="Voice provider returned an invalid ephemeral client secret.")

    return {
        "value": value,
        "expires_at": data.get("expires_at"),
        "session": data.get("session", {}),
        "model": REALTIME_MODEL,
    }


# main.py imports this router before creating its FastAPI app, but the historical
# main.py did not include the router. Automatically attach it only to the Company AI
# app so the endpoint works regardless of whether Render starts main.py or realtime_entry.py.
_original_fastapi_init = FastAPI.__init__


def _company_ai_fastapi_init(self, *args, **kwargs):
    _original_fastapi_init(self, *args, **kwargs)
    if getattr(self, "title", "") == "Company AI Global Business OS":
        self.include_router(router)


FastAPI.__init__ = _company_ai_fastapi_init
