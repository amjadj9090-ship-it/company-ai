from __future__ import annotations

"""Dual-agent council: ChatGPT + Gemini collaborate per Company AI department."""
from dataclasses import dataclass
from typing import Any


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


def decide(department: str, chatgpt: AgentOpinion, gemini: AgentOpinion, *, protected: bool = False) -> CouncilDecision:
    """Select a plan using explicit evidence/risk checks, not model identity.

    A disagreement is resolved by evidence and governance. Confidence alone never
    overrides hard safety constraints. Protected actions always require the owner.
    """
    if protected:
        return CouncilDecision(
            department=department,
            selected_plan=chatgpt.proposal if len(chatgpt.evidence) >= len(gemini.evidence) else gemini.proposal,
            rationale="Both agents reviewed the task; owner approval remains mandatory for the protected operation.",
            needs_owner_approval=True,
        )
    # Prefer the proposal with stronger concrete evidence and fewer stated risks.
    chatgpt_score = len(chatgpt.evidence) - len(chatgpt.risks)
    gemini_score = len(gemini.evidence) - len(gemini.risks)
    if gemini_score > chatgpt_score:
        chosen = gemini
        other = chatgpt
    elif chatgpt_score > gemini_score:
        chosen = chatgpt
        other = gemini
    else:
        # Agreement/tie: keep the plan that is common to both when available;
        # otherwise require a review rather than pretending certainty.
        common = chatgpt.proposal if chatgpt.proposal.strip() == gemini.proposal.strip() else "review_required"
        if common == "review_required":
            return CouncilDecision(department, common, "The two agents did not establish a sufficiently supported common plan.", False)
        chosen, other = chatgpt, gemini
    return CouncilDecision(
        department=department,
        selected_plan=chosen.proposal,
        rationale=f"Selected from {chosen.agent} proposal using evidence/risk comparison; cross-checked against {other.agent}.",
        needs_owner_approval=False,
    )


def manifest() -> dict[str, Any]:
    return {
        "name": "Company AI Dual-Agent Council",
        "model_pair": ["ChatGPT", "Gemini"],
        "departments": {d: ["ChatGPT", "Gemini"] for d in DEPARTMENTS},
        "rule": "Neither model wins by brand; decisions use evidence, risk, governance and verification.",
        "protected_operations": "Owner approval remains mandatory.",
    }
