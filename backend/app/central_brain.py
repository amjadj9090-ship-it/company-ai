from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


@dataclass(frozen=True)
class BrainDecision:
    department: str
    intent: str
    priority: str
    approval_mode: str
    required_approval: bool
    next_actions: tuple[str, ...]


class BrainRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    language: str | None = Field(default=None, max_length=16)
    channel: str = Field(default="website", max_length=40)
    context: dict[str, Any] = Field(default_factory=dict)


class BrainResponse(BaseModel):
    status: str
    decision: dict[str, Any]
    guardrails: dict[str, Any]


_SENSITIVE = (
    "transfer", "withdraw", "bank", "payment", "pay", "contract", "sign", "legal",
    "سحب", "تحويل", "بنك", "دفع", "عقد", "توقيع", "قانوني", "خصم استثنائي", "خصم",
)


def plan(message: str, context: dict[str, Any] | None = None) -> BrainDecision:
    text = message.strip().lower()
    context = context or {}

    if any(k in text for k in _SENSITIVE):
        department = "finance_legal"
        intent = "sensitive_commitment"
        approval_mode = "owner"
        required_approval = True
        priority = "high"
        actions = ("verify_request", "prepare_draft", "create_owner_approval")
    elif any(k in text for k in ("website", "site", "app", "application", "موقع", "تطبيق", "برمجة")):
        department = "digital_services"
        intent = "service_request"
        approval_mode = "auto_standard"
        required_approval = bool(context.get("non_standard"))
        priority = "normal"
        actions = ("qualify_need", "match_approved_package", "prepare_quote")
    elif any(k in text for k in ("lead", "customer", "client", "عميل", "زبون", "شركة", "استفسار")):
        department = "sales_crm"
        intent = "lead_or_customer"
        approval_mode = "auto_standard"
        required_approval = False
        priority = "normal"
        actions = ("capture_context", "qualify_lead", "schedule_follow_up")
    elif any(k in text for k in ("marketing", "campaign", "seo", "إعلان", "تسويق", "حملة")):
        department = "marketing"
        intent = "marketing_request"
        approval_mode = "auto_standard"
        required_approval = bool(context.get("paid_spend"))
        priority = "normal"
        actions = ("define_goal", "prepare_campaign", "measure_results")
    else:
        department = "central_brain"
        intent = "general_business"
        approval_mode = "auto_standard"
        required_approval = False
        priority = "normal"
        actions = ("clarify_intent", "route_to_specialist", "record_decision")

    return BrainDecision(department, intent, priority, approval_mode, required_approval, actions)


@router.post("/api/brain/plan", response_model=BrainResponse)
def brain_plan(request: BrainRequest) -> BrainResponse:
    decision = plan(request.message, request.context)
    return BrainResponse(
        status="ok",
        decision={
            "department": decision.department,
            "intent": decision.intent,
            "priority": decision.priority,
            "approval_mode": decision.approval_mode,
            "required_approval": decision.required_approval,
            "next_actions": list(decision.next_actions),
            "channel": request.channel,
            "language": request.language,
        },
        guardrails={
            "owner_approval_required_for_sensitive_commitments": True,
            "money_movement_allowed_without_owner": False,
            "contract_signing_allowed_without_owner": False,
        },
    )
