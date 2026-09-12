from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from fastapi import HTTPException

from .main import app

OPENAI_REALTIME_CLIENT_SECRETS = "https://api.openai.com/v1/realtime/client_secrets"


@app.post("/api/voice-avatar/public-session")
def create_layan_realtime_client_secret():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Realtime voice service is not configured on the backend.")

    model = os.getenv("REALTIME_MODEL", "gpt-realtime-2.1").strip() or "gpt-realtime-2.1"
    instructions = (
        "You are Layan, the live voice assistant for Company AI. "
        "Speak naturally and professionally. Detect and answer in the visitor's language automatically. "
        "For Arabic, use clear Syrian/Levantine Arabic, never Egyptian phrasing. "
        "Keep answers concise but useful. Never claim that a financial transfer, contract signing, withdrawal, "
        "or other protected commitment was completed without owner approval."
    )
    payload = {
        "expires_after": {"anchor": "created_at", "seconds": 600},
        "session": {
            "type": "realtime",
            "model": model,
            "instructions": instructions,
            "audio": {
                "input": {
                    "noise_reduction": {"type": "near_field"},
                    "turn_detection": {
                        "type": "semantic_vad",
                        "eagerness": "auto",
                        "create_response": True,
                        "interrupt_response": True,
                    },
                    "transcription": {"model": "gpt-4o-transcribe"},
                },
                "output": {"voice": "marin"},
            },
            "output_modalities": ["audio"],
        },
    }
    req = urllib.request.Request(
        OPENAI_REALTIME_CLIENT_SECRETS,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("error", {}).get("message") or body
        except Exception:
            detail = body
        raise HTTPException(status_code=502, detail=f"Realtime provider error: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to create the Realtime session.") from exc

    value = data.get("value")
    if not isinstance(value, str) or not value.startswith("ek_"):
        raise HTTPException(status_code=502, detail="Realtime provider returned no valid ephemeral client secret.")
    return {"value": value, "expires_at": data.get("expires_at"), "session": data.get("session", {})}
