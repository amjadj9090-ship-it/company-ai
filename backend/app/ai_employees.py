from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .central_brain import plan

router = APIRouter()


@dataclass(frozen=True)
class Employee:
    slug: str
    department: str
    capabilities: tuple[str, ...]
    autonomy: str = "supervised"


EMPLOYEES = {
    "sales": Employee("sales", "sales_crm", ("lead qualification", "follow-up", "approved quotes")),
    "marketing": Employee("marketing", "marketing", ("campaign planning", "content", "seo")),
    "web_design": Employee("web_design", "digital_services", ("website scope", "ux", "web proposal")),
    "app_development": Employee("app_development", "app_development", ("app scope", "technical plan", "estimate")),
    "customer_support": Employee("customer_support", "customer_support", ("faq", "customer care", "escalation")),
    "finance": Employee("finance", "finance_legal", ("financial review", "quote review")),
    "legal": Employee("legal", "finance_legal", ("contract review", "risk review")),
    "security": Employee("security", "cybersecurity", ("defensive security review", "authorized assessment", "risk escalation")),
    "monitoring_operations": Employee("monitoring_operations", "monitoring_operations", ("uptime", "alerts", "incident triage", "backups", "operations")),
    "website_growth": Employee("website_growth", "website_growth", ("website audit", "performance", "conversion", "seo", "growth plan")),
    "entrepreneurship": Employee("entrepreneurship", "entrepreneurship", ("business idea", "market analysis", "feasibility study", "startup roadmap")),
    "analytics": Employee("analytics", "central_brain", ("kpi analysis", "business insights")),
    "operations": Employee("operations", "central_brain", ("workflow", "task coordination")),
}


class EmployeeRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    language: str | None = Field(default=None, max_length=16)
    channel: str = Field(default="internal", max_length=40)
    context: dict[str, Any] = Field(default_factory=dict)


class EmployeeResponse(BaseModel):
    status: str
    employee: dict[str, Any]
    decision: dict[str, Any]
    execution: dict[str, Any]


def choose_employee(department: str) -> Employee:
    for employee in EMPLOYEES.values():
        if employee.department == department:
            return employee
    return EMPLOYEES["operations"]


def execute_employee(request: EmployeeRequest) -> EmployeeResponse:
    decision = plan(request.message, request.context)
    employee = choose_employee(decision.department)
    blocked = decision.required_approval
    execution_status = "approval_required" if blocked else "ready_for_execution"
    return EmployeeResponse(
        status="ok",
        employee={
            "slug": employee.slug,
            "department": employee.department,
            "capabilities": list(employee.capabilities),
            "autonomy": employee.autonomy,
        },
        decision={
            "intent": decision.intent,
            "priority": decision.priority,
            "approval_mode": decision.approval_mode,
            "required_approval": decision.required_approval,
            "next_actions": list(decision.next_actions),
        },
        execution={
            "status": execution_status,
            "executed": False if blocked else True,
            "reason": "Owner approval is required before a sensitive commitment." if blocked else "Standard work may proceed within approved permissions.",
        },
    )


@router.get("/api/ai-employees")
def list_employees():
    return {
        "status": "ok",
        "employees": [
            {
                "slug": e.slug,
                "department": e.department,
                "capabilities": list(e.capabilities),
                "autonomy": e.autonomy,
            }
            for e in EMPLOYEES.values()
        ],
    }


@router.post("/api/ai-employees/execute", response_model=EmployeeResponse)
def employee_execute(request: EmployeeRequest) -> EmployeeResponse:
    return execute_employee(request)
