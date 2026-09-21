from __future__ import annotations

"""Company AI dual-agent council: ChatGPT + Gemini per department.

The council is governed by one non-negotiable objective: protect and advance
Company AI's legitimate business interests while respecting security,
authorization, legal/financial approval and verification requirements.
"""

from dataclasses import dataclass
from typing import Any
import json
import os
import urllib.request


@dataclass(frozen=True)
class AgentOpinion:
    agent: str
    proposal: str
    evidence: list[str]
    risks: list[str]
    confidence: float


@dataclass(frozen=True)
class CouncilDecision:
    department: str
    selected_plan: str
    rationale: str
    needs_owner_approval: bool
    participants: tuple[str, ...] = ("chatgpt", "gemini")
    status: str = "selected"


DEPARTMENTS = (
    "central", "sales", "marketing", "lead_generation", "growth", "trade",
    "customer_support", "web_design", "app_development", "uiux", "frontend",
    "qa", "operations", "analytics", "finance", "legal", "security",
    "partnerships", "product", "seo", "entrepreneurship", "website_growth",
    "cybersecurity", "monitoring_operations", "agent_builder", "voice_avatar",
)


def agents_for_department(department: str) -> tuple[str, str]:
    if department not in DEPARTMENTS:
        raise ValueError(f"Unknown Company AI department: {department}")
    return ("chatgpt", "gemini")


def _company_objective(department: str, message: str) -> str:
    return (
        "PRIMARY OBJECTIVE: advance the legitimate long-term interests of Company AI. "
        "Choose the most correct, useful, secure, maintainable and evidence-supported plan. "
        "Do not choose by model brand. Do not hide disagreement. "
        "Never trade away security, authorization, legal compliance, owner approval or data protection "
        "for speed or convenience. A claim of certainty is never evidence by itself. "
        f"Department: {department}. Request: {message.strip()}"
    )


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 45) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _chatgpt_opinion(department: str, message: str) -> AgentOpinion:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    model = os.getenv("OPENAI_COUNCIL_MODEL", "gpt-5").strip() or "gpt-5"
    prompt = (
        _company_objective(department, message)
        + "\nReturn JSON with exactly: proposal (string), evidence (array of strings), "
        "risks (array of strings), confidence (number 0..1). "
        "Evidence must be concrete and relevant; risks must include uncertainty or missing verification."
    )
    data = _post_json(
        "https://api.openai.com/v1/responses",
        {"model": model, "input": prompt, "store": False},
        {"Authorization": f"Bearer {key}"},
    )
    text = str(data.get("output_text", "")).strip()
    if not text:
        for item in data.get("output", []):
            for part in item.get("content", []) if isinstance(item, dict) else []:
                if part.get("type") == "output_text":
                    text += str(part.get("text", ""))
    parsed = json.loads(text)
    return AgentOpinion(
        "chatgpt", str(parsed["proposal"]), list(parsed.get("evidence", [])),
        list(parsed.get("risks", [])), float(parsed.get("confidence", 0)),
    )


def _gemini_opinion(department: str, message: str) -> AgentOpinion:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    model = os.getenv("GEMINI_COUNCIL_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")).strip()
    prompt = (
        _company_objective(department, message)
        + "\nReturn JSON only with exactly: proposal (string), evidence (array of strings), "
        "risks (array of strings), confidence (number 0..1). "
        "Evidence must be concrete and relevant; risks must include uncertainty or missing verification."
    )
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {
            "system_instruction": {"parts": [{"text": "You are the Gemini member of the Company AI council. " + _company_objective(department, message)}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.15, "responseMimeType": "application/json"},
        },
        {"x-goog-api-key": key},
    )
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
    parsed = json.loads(text)
    return AgentOpinion(
        "gemini", str(parsed["proposal"]), list(parsed.get("evidence", [])),
        list(parsed.get("risks", [])), float(parsed.get("confidence", 0)),
    )


def decide(department: str, chatgpt: AgentOpinion, gemini: AgentOpinion, *, protected: bool = False) -> CouncilDecision:
    """Resolve disagreement by evidence, verification and risk—not model identity."""
    if protected:
        return CouncilDecision(
            department, "review_required",
            "Protected operation: both agents may prepare the plan, but owner approval is mandatory before execution.",
            True, status="owner_approval_required",
        )

    gpt_score = len(chatgpt.evidence) - 2 * len(chatgpt.risks)
    gem_score = len(gemini.evidence) - 2 * len(gemini.risks)
    if chatgpt.proposal.strip() == gemini.proposal.strip():
        return CouncilDecision(department, chatgpt.proposal, "Both agents independently produced the same plan; retain it and verify execution.", False)
    if gpt_score == gem_score:
        return CouncilDecision(
            department, "review_required",
            "The proposals remain materially different with no evidence-based separation. Do not guess; require additional verification.",
            False, status="verification_required",
        )
    chosen = chatgpt if gpt_score > gem_score else gemini
    other = gemini if chosen is chatgpt else chatgpt
    return CouncilDecision(
        department, chosen.proposal,
        f"Selected {chosen.agent} because its proposal had stronger evidence/risk support than {other.agent}. "
        "The selected plan still requires validation before consequential execution.",
        False,
    )


def run_council(department: str, message: str, *, protected: bool = False) -> dict[str, Any]:
    """Run both agents, preserve disagreement, and return a governed decision."""
    if department not in DEPARTMENTS:
        raise ValueError(f"Unknown Company AI department: {department}")
    errors: dict[str, str] = {}
    opinions: dict[str, AgentOpinion] = {}
    for name, fn in (("chatgpt", _chatgpt_opinion), ("gemini", _gemini_opinion)):
        try:
            opinions[name] = fn(department, message)
        except Exception as exc:
            errors[name] = exc.__class__.__name__

    if len(opinions) < 2:
        return {
            "status": "verification_required",
            "department": department,
            "objective": "Company AI legitimate business interest is the highest business objective within governance.",
            "participants": ["chatgpt", "gemini"],
            "available_agents": list(opinions),
            "errors": errors,
            "decision": None,
        }

    decision = decide(department, opinions["chatgpt"], opinions["gemini"], protected=protected)
    return {
        "status": decision.status,
        "department": department,
        "objective": "Company AI legitimate business interest is the highest business objective within governance.",
        "participants": ["chatgpt", "gemini"],
        "opinions": {
            k: {"proposal": v.proposal, "evidence": v.evidence, "risks": v.risks, "confidence": v.confidence}
            for k, v in opinions.items()
        },
        "decision": {
            "selected_plan": decision.selected_plan,
            "rationale": decision.rationale,
            "needs_owner_approval": decision.needs_owner_approval,
        },
        "errors": errors,
    }


def manifest() -> dict[str, Any]:
    return {
        "name": "Company AI Dual-Agent Council",
        "model_pair": ["ChatGPT", "Gemini"],
        "departments": {d: ["ChatGPT", "Gemini"] for d in DEPARTMENTS},
        "primary_objective": "Company AI legitimate business interest, subject to security, authorization, law and owner approvals.",
        "selection_rule": "Evidence + verification + risk + governance. Never model-brand preference.",
        "disagreement_rule": "No forced winner when evidence is insufficient; request verification.",
        "protected_operations": "Owner approval remains mandatory.",
    }
