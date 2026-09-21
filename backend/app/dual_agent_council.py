from __future__ import annotations

"""Collaborative ChatGPT + Gemini teams for Company AI.

Two agents are teammates on one shared task. They inspect, propose, cross-review,
revise, converge, and verify. Central Brain coordinates the rounds and governance;
it does not pick a model winner.
"""

from dataclasses import dataclass
from typing import Any
import json
import os
import urllib.request
from .agent_tooling import capability_manifest, gemini_tools, openai_tools, tool_policy_prompt


@dataclass(frozen=True)
class AgentOpinion:
    agent: str
    proposal: str
    evidence: list[str]
    risks: list[str]
    confidence: float


@dataclass(frozen=True)
class CollaborativeRound:
    number: int
    phase: str
    chatgpt: AgentOpinion | None = None
    gemini: AgentOpinion | None = None


@dataclass(frozen=True)
class CouncilDecision:
    department: str
    selected_plan: str
    rationale: str
    needs_owner_approval: bool
    participants: tuple[str, ...] = ("chatgpt", "gemini")
    status: str = "collaborative_plan_ready"


DEPARTMENTS = (
    "central", "sales", "marketing", "lead_generation", "growth", "trade",
    "customer_support", "web_design", "app_development", "uiux", "frontend",
    "qa", "operations", "analytics", "finance", "legal", "security",
    "partnerships", "product", "seo", "entrepreneurship", "website_growth",
    "cybersecurity", "monitoring_operations", "agent_builder", "voice_avatar",
)

MAX_COLLABORATION_ROUNDS = int(os.getenv("COMPANY_AI_COLLAB_ROUNDS", "2"))


def agents_for_department(department: str) -> tuple[str, str]:
    if department not in DEPARTMENTS:
        raise ValueError(f"Unknown Company AI department: {department}")
    return ("chatgpt", "gemini")


def _company_objective(department: str, message: str) -> str:
    return (
        "PRIMARY BUSINESS OBJECTIVE: advance Company AI's legitimate long-term interests "
        "by producing the most correct, useful, secure, maintainable and evidence-supported result. "
        "ChatGPT and Gemini are teammates, not competitors. Neither model is the winner. "
        "They must share relevant context, challenge weak assumptions, correct each other, "
        "and converge on one shared plan. Never trade away security, authorization, legal compliance, "
        "owner approval or data protection for speed. "
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


def _parse_opinion(agent: str, text: str) -> AgentOpinion:
    parsed = json.loads(text)
    return AgentOpinion(
        agent,
        str(parsed["proposal"]),
        [str(x) for x in parsed.get("evidence", [])],
        [str(x) for x in parsed.get("risks", [])],
        max(0.0, min(1.0, float(parsed.get("confidence", 0)))),
    )


def _chatgpt_call(prompt: str) -> AgentOpinion:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    model = os.getenv("OPENAI_COUNCIL_MODEL", "gpt-5").strip() or "gpt-5"
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
    return _parse_opinion("chatgpt", text)


def _gemini_call(prompt: str) -> AgentOpinion:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    model = os.getenv("GEMINI_COUNCIL_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")).strip()
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {
            "system_instruction": {"parts": [{"text": "You are the Gemini teammate in Company AI. " + prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.15, "responseMimeType": "application/json"},
        },
        {"x-goog-api-key": key},
    )
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
    return _parse_opinion("gemini", text)


def _round_prompt(objective: str, phase: str, own: AgentOpinion | None = None,
                  peer: AgentOpinion | None = None) -> str:
    schema = (
        "Return JSON only with exactly: proposal (string), evidence (array of strings), "
        "risks (array of strings), confidence (number 0..1). "
        "Proposal must describe the shared solution, not a model-specific victory."
    )
    if phase == "initial":
        return f"{objective}\nPHASE: initial joint-team analysis.\n{schema}"
    return (
        f"{objective}\nPHASE: cross-review and convergence.\n"
        f"Your previous proposal:\n{own.proposal if own else ''}\n"
        f"Your previous evidence:\n{json.dumps(own.evidence if own else [])}\n"
        f"Your previous risks:\n{json.dumps(own.risks if own else [])}\n"
        f"Teammate proposal:\n{peer.proposal if peer else ''}\n"
        f"Teammate evidence:\n{json.dumps(peer.evidence if peer else [])}\n"
        f"Teammate risks:\n{json.dumps(peer.risks if peer else [])}\n"
        "Keep strong parts from both sides. Correct factual or technical weaknesses. "
        "Explicitly incorporate useful teammate contributions. If disagreement remains, "
        f"state what must be tested or verified rather than choosing a winner.\n{schema}"
    )


def _run_pair(prompt: str) -> tuple[AgentOpinion, AgentOpinion]:
    errors: list[Exception] = []
    results: dict[str, AgentOpinion] = {}
    for name, fn in (("chatgpt", _chatgpt_call), ("gemini", _gemini_call)):
        try:
            results[name] = fn(prompt)
        except Exception as exc:
            errors.append(exc)
    if errors:
        raise RuntimeError("; ".join(f"{e.__class__.__name__}: {e}" for e in errors))
    return results["chatgpt"], results["gemini"]


def _build_shared_plan(rounds: list[CollaborativeRound]) -> str:
    """Merge the latest team outputs without ranking either model."""
    latest = rounds[-1]
    g, m = latest.chatgpt, latest.gemini
    if not g or not m:
        return "verification_required"
    if g.proposal.strip() == m.proposal.strip():
        return g.proposal.strip()
    return (
        "SHARED COLLABORATIVE PLAN\n"
        "1. Combine the useful requirements and implementation ideas from both teammates.\n"
        f"- ChatGPT contribution: {g.proposal.strip()}\n"
        f"- Gemini contribution: {m.proposal.strip()}\n"
        "2. Preserve non-conflicting evidence from both teammates.\n"
        "3. Resolve conflicts by testing, repository evidence, or explicit verification—not model identity.\n"
        "4. Implement the shared plan, cross-review the implementation, run tests, and fix failures before release.\n"
    )


def decide(department: str, chatgpt: AgentOpinion, gemini: AgentOpinion,
           *, protected: bool = False, rounds: list[CollaborativeRound] | None = None) -> CouncilDecision:
    """Return the shared team plan; never select a model winner."""
    shared = _build_shared_plan(rounds or [CollaborativeRound(1, "initial", chatgpt, gemini)])
    if protected:
        return CouncilDecision(
            department, shared,
            "Both teammates collaborate on preparation, but owner approval remains mandatory before execution.",
            True, status="owner_approval_required",
        )
    return CouncilDecision(
        department, shared,
        "ChatGPT and Gemini jointly contributed, cross-reviewed and converged. "
        "Remaining conflicts are resolved by evidence/tests, not by choosing a model winner.",
        False,
    )


def run_council(department: str, message: str, *, protected: bool = False) -> dict[str, Any]:
    """Run a bounded collaborative pair workflow with shared context and verification gates."""
    if department not in DEPARTMENTS:
        raise ValueError(f"Unknown Company AI department: {department}")

    objective = _company_objective(department, message)
    errors: dict[str, str] = {}
    rounds: list[CollaborativeRound] = []

    try:
        chatgpt, gemini = _run_pair(_round_prompt(objective, "initial"))
        rounds.append(CollaborativeRound(1, "initial", chatgpt, gemini))

        # Cross-review: each teammate sees the other's work and revises the same shared task.
        for number in range(2, max(1, MAX_COLLABORATION_ROUNDS) + 1):
            try:
                chatgpt = _chatgpt_call(_round_prompt(objective, "cross_review", chatgpt, gemini))
                gemini = _gemini_call(_round_prompt(objective, "cross_review", gemini, chatgpt))
                rounds.append(CollaborativeRound(number, "cross_review", chatgpt, gemini))
            except Exception as exc:
                errors["cross_review"] = f"{exc.__class__.__name__}: {exc}"
                break
    except Exception as exc:
        errors["initial_round"] = f"{exc.__class__.__name__}: {exc}"

    if not rounds or not rounds[-1].chatgpt or not rounds[-1].gemini:
        return {
            "status": "verification_required",
            "department": department,
            "objective": objective,
            "participants": ["chatgpt", "gemini"],
            "collaboration_mode": "shared_task_cross_review_convergence",
            "rounds_completed": len(rounds),
            "errors": errors,
            "decision": None,
        }

    decision = decide(
        department, rounds[-1].chatgpt, rounds[-1].gemini,
        protected=protected, rounds=rounds,
    )
    return {
        "status": decision.status,
        "department": department,
        "objective": objective,
        "participants": ["chatgpt", "gemini"],
        "collaboration_mode": "shared_task_cross_review_convergence",
        "rounds_completed": len(rounds),
        "max_rounds": MAX_COLLABORATION_ROUNDS,
        "rounds": [
            {
                "number": r.number,
                "phase": r.phase,
                "chatgpt": _opinion_dict(r.chatgpt),
                "gemini": _opinion_dict(r.gemini),
            }
            for r in rounds
        ],
        "shared_plan": decision.selected_plan,
        "decision": {
            "selected_plan": decision.selected_plan,
            "rationale": decision.rationale,
            "needs_owner_approval": decision.needs_owner_approval,
        },
        "verification": {
            "required": True,
            "rule": "Implement -> cross-review -> automated tests -> fix failures -> final verification.",
        },
        "errors": errors,
    }


def _opinion_dict(value: AgentOpinion | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "proposal": value.proposal,
        "evidence": value.evidence,
        "risks": value.risks,
        "confidence": value.confidence,
    }


def manifest() -> dict[str, Any]:
    return {
        "name": "Company AI Collaborative Dual-Agent Team",
        "model_pair": ["ChatGPT", "Gemini"],
        "departments": {d: ["ChatGPT", "Gemini"] for d in DEPARTMENTS},
        "mode": "shared_task_cross_review_convergence",
        "primary_objective": "Company AI legitimate business interest, subject to security, authorization, law and owner approvals.",
        "workflow": [
            "inspect shared task",
            "initial proposals",
            "share context",
            "cross-review",
            "revise together",
            "converge on shared plan",
            "implement",
            "cross-review implementation",
            "test",
            "fix",
            "final verification",
        ],
        "selection_rule": "No model winner. Resolve disagreements with evidence, tests and verification.",
        "max_rounds": MAX_COLLABORATION_ROUNDS,
        "protected_operations": "Owner approval remains mandatory.",
    }
