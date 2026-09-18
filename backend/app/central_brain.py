from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from .specialist_agents import execute_specialist

router = APIRouter()


@dataclass(frozen=True)
class BrainDecision:
    department: str
    intent: str
    priority: str
    approval_mode: str
    required_approval: bool
    next_actions: tuple[str, ...]

    @property
    def requires_owner_approval(self) -> bool:
        """Backward-compatible alias used by older CRM integrations."""
        return self.required_approval


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
    elif any(k in text for k in ("feasibility", "business plan", "startup", "جدوى", "ريادة", "مشروع جديد", "استشارة مجانية", "استشارة أولية")):
        department = "entrepreneurship"
        intent = "entrepreneurship_or_feasibility"
        approval_mode = "auto_standard"
        required_approval = False
        priority = "normal"
        actions = ("qualify_idea", "analyze_market", "prepare_feasibility_or_roadmap")
    elif any(k in text for k in ("cybersecurity", "cyber security", "security audit", "أمن سيبراني", "حماية رقمية", "اختبار أمني", "ثغرات")):
        department = "cybersecurity"
        intent = "cybersecurity_request"
        approval_mode = "supervised"
        required_approval = bool(context.get("authorized_testing")) is False
        priority = "high"
        actions = ("define_scope", "verify_authorization", "prepare_defensive_assessment")
    elif any(k in text for k in ("monitoring", "operations", "uptime", "monitor", "مراقبة", "تشغيل مستمر", "تشغيل", "أعطال", "نسخ احتياطية")):
        department = "monitoring_operations"
        intent = "monitoring_operations_request"
        approval_mode = "auto_standard"
        required_approval = False
        priority = "normal"
        actions = ("inspect_services", "define_alerts", "prepare_operations_plan")
    elif any(k in text for k in ("website growth", "website audit", "site audit", "نمو الموقع", "فحص الموقع", "تقييم الموقع", "تحسين الموقع")):
        department = "website_growth"
        intent = "website_growth_request"
        approval_mode = "auto_standard"
        required_approval = False
        priority = "normal"
        actions = ("inspect_site", "identify_growth_gaps", "prepare_optimization_plan")
    elif any(k in text for k in ("customer support", "support", "خدمة العملاء", "دعم العملاء", "شكاوى")):
        department = "customer_support"
        intent = "customer_support_request"
        approval_mode = "auto_standard"
        required_approval = False
        priority = "normal"
        actions = ("capture_context", "resolve_standard_request", "escalate_if_needed")
    elif any(k in text for k in ("app", "application", "mobile", "تطبيق", "ابلكيشن")):
        department = "app_development"
        intent = "app_development_request"
        approval_mode = "auto_standard"
        required_approval = bool(context.get("non_standard"))
        priority = "normal"
        actions = ("qualify_need", "define_app_scope", "prepare_technical_plan")
    elif any(k in text for k in ("website", "site", "موقع", "برمجة")):
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


def _persist_orchestration(request: BrainRequest, decision: BrainDecision) -> dict[str, Any]:
    """Persist a Central AI decision/task without executing protected operations."""
    try:
        from .main import Entity, Approval, Audit, engine, now
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            timestamp = now()
            plan_entity = Entity(
                kind="central_plan",
                data={
                    "message": request.message,
                    "language": request.language or "auto",
                    "channel": request.channel,
                    "context": request.context,
                    "department": decision.department,
                    "intent": decision.intent,
                    "priority": decision.priority,
                    "approval_required": decision.required_approval,
                    "status": "awaiting_owner_approval" if decision.required_approval else "planned",
                },
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(plan_entity)
            db.flush()
            task = Entity(
                kind="central_task",
                data={
                    "plan_id": plan_entity.id,
                    "department": decision.department,
                    "actions": list(decision.next_actions),
                    "status": "blocked_pending_owner" if decision.required_approval else "ready",
                },
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(task)
            db.flush()
            decision_entity = Entity(
                kind="central_decision",
                data={
                    "plan_id": plan_entity.id,
                    "task_id": task.id,
                    "department": decision.department,
                    "intent": decision.intent,
                    "approval_mode": decision.approval_mode,
                    "required_approval": decision.required_approval,
                    "actions": list(decision.next_actions),
                },
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(decision_entity)
            db.flush()
            if decision.required_approval:
                db.add(Approval(
                    action="central_ai_approval",
                    entity_type="central_plan",
                    entity_id=plan_entity.id,
                    reason="Protected operation requires owner approval before execution.",
                    status="pending",
                    requested_by=f"central-ai:{request.channel}",
                    created_at=timestamp,
                    updated_at=timestamp,
                ))
            db.add(Audit(
                actor=f"central-ai:{request.channel}",
                action="plan_created",
                entity="central_plan",
                entity_id=plan_entity.id,
                details={"department": decision.department, "intent": decision.intent},
                created_at=timestamp,
            ))
            db.commit()
            return {"plan_id": plan_entity.id, "task_id": task.id, "decision_id": decision_entity.id}
    except Exception:
        return {"plan_id": None, "task_id": None, "decision_id": None}


@router.post("/api/central-ai/execute", response_model=BrainResponse)
def central_ai_execute(request: dict[str, Any]) -> BrainResponse:
    plan_id = int(request.get("plan_id", 0))
    confirm = bool(request.get("confirm", False))
    if plan_id <= 0:
        raise HTTPException(status_code=400, detail="plan_id is required")
    try:
        from .main import Entity, Approval, Audit, engine, now
        from sqlalchemy.orm import Session
        with Session(engine) as db:
            plan_entity = db.get(Entity, plan_id)
            if not plan_entity or plan_entity.kind != "central_plan":
                raise HTTPException(status_code=404, detail="Central plan not found")
            data = plan_entity.data or {}
            if data.get("approval_required"):
                approved = db.query(Approval).filter(
                    Approval.entity_type == "central_plan",
                    Approval.entity_id == plan_id,
                    Approval.status == "approved",
                ).first()
                if not approved:
                    result = {"status": "blocked_pending_owner", "reason": "Owner approval is required before execution."}
                else:
                    result = execute_specialist(data["department"], data["message"], data.get("actions", []), owner_approved=True)
            elif not confirm:
                result = {"status": "awaiting_confirmation", "reason": "Explicit execution confirmation is required."}
            else:
                task = db.query(Entity).filter(
                    Entity.kind == "central_task",
                    Entity.data["plan_id"].as_integer() == plan_id,
                ).first()
                result = execute_specialist(data["department"], data["message"], task.data.get("actions", []) if task else [])
            execution = Entity(
                kind="specialist_execution",
                data={"plan_id": plan_id, "department": data.get("department"), "result": result},
                created_at=now(), updated_at=now(),
            )
            db.add(execution)
            db.flush()
            if result.get("status") == "completed":
                plan_entity.data = {**data, "status": "completed", "execution_id": execution.id}
            elif result.get("status") == "blocked_pending_owner":
                plan_entity.data = {**data, "status": "awaiting_owner_approval"}
            db.add(Audit(actor="central-ai", action="specialist_execution", entity="central_plan", entity_id=plan_id, details=result, created_at=now()))
            db.commit()
            return BrainResponse(
                status=result.get("status", "blocked"),
                decision={"plan_id": plan_id, "department": data.get("department"), "execution": result},
                guardrails={"owner_approval_required_for_sensitive_commitments": True},
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Specialist execution failed: {exc.__class__.__name__}") from exc


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
