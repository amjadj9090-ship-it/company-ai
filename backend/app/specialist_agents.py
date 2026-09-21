from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SpecialistAgent:
    department: str
    agent_name: str
    mission: str
    actions: tuple[str, ...]
    protected: bool = False


SPECIALISTS: dict[str, SpecialistAgent] = {
    "digital_services": SpecialistAgent("digital_services", "web_design", "qualify and scope website services", ("qualify_need", "match_approved_package", "prepare_quote")),
    "app_development": SpecialistAgent("app_development", "app_development", "qualify and scope application work", ("qualify_need", "define_app_scope", "prepare_technical_plan")),
    "sales_crm": SpecialistAgent("sales_crm", "sales", "capture and qualify customer opportunities", ("capture_context", "qualify_lead", "schedule_follow_up")),
    "marketing": SpecialistAgent("marketing", "marketing", "prepare measurable marketing campaigns", ("define_goal", "prepare_campaign", "measure_results")),
    "entrepreneurship": SpecialistAgent("entrepreneurship", "entrepreneurship", "qualify ideas and prepare feasibility roadmaps", ("qualify_idea", "analyze_market", "prepare_feasibility_or_roadmap")),
    "website_growth": SpecialistAgent("website_growth", "website_growth", "audit and improve website growth", ("inspect_site", "identify_growth_gaps", "prepare_optimization_plan")),
    "customer_support": SpecialistAgent("customer_support", "customer_support", "resolve standard customer requests and escalate exceptions", ("capture_context", "resolve_standard_request", "escalate_if_needed")),
    "monitoring_operations": SpecialistAgent("monitoring_operations", "monitoring_operations", "inspect service health and operational risks", ("inspect_services", "define_alerts", "prepare_operations_plan")),
    "cybersecurity": SpecialistAgent("cybersecurity", "cybersecurity", "perform authorized defensive security planning", ("define_scope", "verify_authorization", "prepare_defensive_assessment"), True),
    "finance_legal": SpecialistAgent("finance_legal", "finance", "prepare protected finance/legal work for owner review", ("verify_request", "prepare_draft", "create_owner_approval"), True),
    "central_brain": SpecialistAgent("central_brain", "central", "clarify and route business work", ("clarify_intent", "route_to_specialist", "record_decision")),
    "gemini_agent": SpecialistAgent("gemini_agent", "gemini", "first-class Company AI Gemini agent for inspection, coding, testing, debugging and collaboration", ("inspect_company_ai", "inspect_layan", "propose_changes", "write_approved_code", "test_and_debug", "collaborate_with_company_ai_agents", "use_approved_company_tools")),
}


def get_specialist(department: str) -> SpecialistAgent | None:
    return SPECIALISTS.get(department)


def execute_specialist(
    department: str,
    message: str,
    planned_actions: list[str],
    *,
    owner_approved: bool = False,
) -> dict[str, Any]:
    agent = get_specialist(department)
    if agent is None:
        return {"status": "blocked", "reason": "No registered specialist for department"}

    if agent.protected and not owner_approved:
        return {
            "status": "blocked_pending_owner",
            "agent": agent.agent_name,
            "department": department,
            "reason": "Owner approval is required before protected execution.",
            "actions": list(agent.actions),
        }

    actions = [a for a in planned_actions if a in agent.actions] or list(agent.actions)
    return {
        "status": "completed",
        "agent": agent.agent_name,
        "department": department,
        "mission": agent.mission,
        "message_received": True,
        "actions_executed": actions,
        "result": "specialist_plan_completed",
        "protected": agent.protected,
    }
