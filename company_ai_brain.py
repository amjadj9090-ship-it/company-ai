from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any
import uuid
from company_ai_ops import ops
from backend.app.specialist_agents import execute_specialist

@dataclass(frozen=True)
class BrainDecision:
    department: str
    intent: str
    priority: str
    approval_mode: str
    required_approval: bool
    next_actions: tuple[str, ...]

SENSITIVE = (
    "transfer", "withdraw", "bank", "payment", "pay", "contract", "sign", "legal",
    "سحب", "تحويل", "بنك", "دفع", "دفع", "عقد", "توقيع", "قانوني", "خصم استثنائي",
)

def analyze(message: str, context: dict[str, Any] | None = None) -> BrainDecision:
    text = message.strip().lower()
    context = context or {}
    if any(k in text for k in SENSITIVE):
        return BrainDecision("finance_legal", "sensitive_commitment", "high", "owner", True,
                             ("verify_request", "prepare_draft", "create_owner_approval"))
    if any(k in text for k in ("website growth","website audit","site audit","نمو الموقع","فحص الموقع","تقييم الموقع","تحسين الموقع")):
        return BrainDecision("website_growth","website_growth_request","normal","auto_standard",False,
                             ("inspect_site","identify_growth_gaps","prepare_optimization_plan"))
    if any(k in text for k in ("cybersecurity","cyber security","security audit","أمن سيبراني","حماية رقمية","اختبار أمني","ثغرات")):
        return BrainDecision("cybersecurity","cybersecurity_request","high",
                             "supervised" if not context.get("authorized_testing") else "auto_standard",
                             not bool(context.get("authorized_testing")),
                             ("define_scope","verify_authorization","prepare_defensive_assessment"))
    if any(k in text for k in ("monitoring","operations","uptime","monitor","مراقبة","تشغيل مستمر","أعطال","نسخ احتياطية")):
        return BrainDecision("monitoring_operations","monitoring_operations_request","normal","auto_standard",False,
                             ("inspect_services","define_alerts","prepare_operations_plan"))
    if any(k in text for k in ("app","application","mobile","تطبيق","ابلكيشن")):
        return BrainDecision("app_development","app_development_request","normal",
                             "owner" if context.get("non_standard") else "auto_standard",
                             bool(context.get("non_standard")),
                             ("qualify_need","define_app_scope","prepare_technical_plan"))
    if any(k in text for k in ("website","site","موقع","برمجة")):
        return BrainDecision("digital_services","service_request","normal",
                             "owner" if context.get("non_standard") else "auto_standard",
                             bool(context.get("non_standard")),
                             ("qualify_need","match_approved_package","prepare_quote"))
    if any(k in text for k in ("marketing","campaign","seo","إعلان","تسويق","حملة")):
        return BrainDecision("marketing","marketing_request","normal",
                             "owner" if context.get("paid_spend") else "auto_standard",
                             bool(context.get("paid_spend")),
                             ("define_goal","prepare_campaign","measure_results"))
    if any(k in text for k in ("lead","customer","client","عميل","زبون","شركة","استفسار")):
        return BrainDecision("sales_crm","lead_or_customer","normal","auto_standard",False,
                             ("capture_context","qualify_lead","schedule_follow_up"))
    if any(k in text for k in ("feasibility","business plan","startup","جدوى","ريادة","مشروع جديد")):
        return BrainDecision("entrepreneurship","entrepreneurship_or_feasibility","normal","auto_standard",False,
                             ("qualify_idea","analyze_market","prepare_feasibility_or_roadmap"))
    return BrainDecision("central_brain","general_business","normal","auto_standard",False,
                         ("understand_intent","route_to_specialist","record_decision"))

class CentralBrain:
    def __init__(self) -> None:
        self._plans: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create_plan(self, message: str, *, language: str = "auto", channel: str = "web",
                    context: dict[str, Any] | None = None) -> dict[str, Any]:
        decision = analyze(message, context)
        plan_id = "plan_" + uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        task = ops.create_task(
            "Process Central AI request",
            decision.department,
            approval_required=decision.required_approval,
            next_actions=decision.next_actions,
        )
        plan = {
            "plan_id": plan_id, "created_at": now, "updated_at": now,
            "message": message, "language": language, "channel": channel,
            "context": context or {}, "status": "awaiting_owner_approval" if decision.required_approval else "planned",
            "decision": asdict(decision),
            "task_id": task["task_id"],
            "guardrails": {
                "owner_approval_required_for_sensitive_commitments": True,
                "money_movement_allowed_without_owner": False,
                "contract_signing_allowed_without_owner": False,
            },
        }
        execution = execute_specialist(
            decision.department,
            message,
            list(decision.next_actions),
            owner_approved=False,
        )
        if execution.get("status") == "completed":
            plan["status"] = "completed"
            plan["execution"] = execution
            task = ops.mark_handoff_ready(task["task_id"])
            if task:
                task["status"] = "completed"
                task["execution"] = execution
        else:
            plan["execution"] = execution
        with self._lock:
            self._plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._plans.get(plan_id)

    def advance(self, plan_id: str, *, confirm: bool = False, owner_approved: bool = False) -> dict[str, Any]:
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                return {"status": "not_found", "plan_id": plan_id}
            if plan["decision"]["required_approval"] and not owner_approved:
                plan["status"] = "awaiting_owner_approval"
                plan["updated_at"] = datetime.now(timezone.utc).isoformat()
                return {"status": plan["status"], "plan_id": plan_id}
            if not confirm:
                return {"status": "awaiting_confirmation", "plan_id": plan_id}
            plan["status"] = "ready_for_specialist"
            plan["updated_at"] = datetime.now(timezone.utc).isoformat()
            task = ops.mark_handoff_ready(plan["task_id"])
            return {
                "status": plan["status"],
                "plan_id": plan_id,
                "department": plan["decision"]["department"],
                "task": task,
            }

    def all_plans(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._plans.values())

brain = CentralBrain()
