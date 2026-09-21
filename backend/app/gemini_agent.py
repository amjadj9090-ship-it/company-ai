from __future__ import annotations

"""First-class Gemini agent definition for Company AI.

Gemini is an internal Company AI agent/provider, not a separate company or product.
It shares the same governance rules as the other Company AI agents.
"""

from dataclasses import dataclass
from typing import Any
import json
import os
import urllib.request


@dataclass(frozen=True)
class GeminiAgentPolicy:
    name: str = "gemini"
    display_name: str = "Gemini Agent"
    role: str = "general company AI agent"
    status: str = "active"
    permissions: tuple[str, ...] = (
        "inspect_company_ai",
        "inspect_layan",
        "propose_changes",
        "write_approved_code",
        "test_and_debug",
        "collaborate_with_company_ai_agents",
        "use_approved_company_tools",
    )
    owner_approval_required: tuple[str, ...] = (
        "money_movement",
        "bank_transfer",
        "withdrawal",
        "binding_contract",
        "legal_commitment",
        "non_standard_financial_commitment",
    )
    forbidden: tuple[str, ...] = (
        "change_or_reveal_secrets_without_approved_secret_workflow",
        "self_escalate_permissions",
        "bypass_company_governance",
        "sign_binding_contracts",
        "move_company_money_without_owner_approval",
    )


POLICY = GeminiAgentPolicy()


def manifest() -> dict[str, Any]:
    return {
        "id": POLICY.name,
        "name": POLICY.display_name,
        "role": POLICY.role,
        "status": POLICY.status,
        "provider": "Google Gemini API",
        "permissions": list(POLICY.permissions),
        "owner_approval_required": list(POLICY.owner_approval_required),
        "forbidden": list(POLICY.forbidden),
        "scope": "Company AI internal agent; includes Layan inspection, debugging and improvement.",
    }


def is_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def ask(message: str, history: list[dict[str, Any]] | None = None) -> str:
    """Send a governed internal-agent request to Gemini.

    This function never grants Gemini access to secrets or protected operations.
    The Company AI approval layer remains authoritative for protected actions.
    """
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    contents = []
    for item in (history or [])[-10:]:
        role = "model" if item.get("role") in {"assistant", "model"} else "user"
        text = str(item.get("text") or item.get("content") or "").strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text[:8000]}]})
    contents.append({"role": "user", "parts": [{"text": message.strip()}]})

    system = (
        "You are Gemini Agent, a first-class internal agent of Company AI. "
        "You may inspect, propose, modify, test and debug Company AI code and Layan when the request is within scope. "
        "Treat ChatGPT agents and Gemini agents as peers under the same Company AI governance. "
        "Never move money, sign a binding contract, make a legal commitment, or make a non-standard financial commitment without owner approval. "
        "Never reveal or change secrets/API keys except through the approved secret-management workflow. "
        "Never escalate your own permissions or bypass governance. "
        "Do not claim an action was completed unless Company AI actually completed it."
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 1200},
    }
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    reply = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
    if not reply:
        raise RuntimeError("Gemini returned an empty response")
    return reply
