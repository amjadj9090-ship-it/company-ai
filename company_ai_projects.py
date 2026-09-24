from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
import uuid

from company_ai_brain import analyze
from company_ai_ops import ops, AGENTS

STAGES = ("intake", "planned", "awaiting_owner_approval", "executing", "qa", "ready_for_delivery", "delivered")

class ProjectOps:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create(self, name: str, request: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        decision = analyze(request, context or {})
        project_id = "proj_" + uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        status = "awaiting_owner_approval" if decision.required_approval else "planned"
        project = {
            "project_id": project_id,
            "name": name,
            "request": request,
            "created_at": now,
            "updated_at": now,
            "status": status,
            "department": decision.department,
            "intent": decision.intent,
            "priority": decision.priority,
            "approval_required": decision.required_approval,
            "owner_approved": False,
            "agent": AGENTS.get(decision.department, {"name": "Central AI", "capabilities": ["general_business_routing"]}),
            "next_actions": list(decision.next_actions),
            "task_ids": [],
            "qa": {"status": "not_started", "checks": []},
        }
        with self._lock:
            self.projects[project_id] = project

        for action in decision.next_actions:
            task = ops.create_task(
                action.replace("_", " ").title(),
                decision.department,
                approval_required=decision.required_approval,
            )
            project["task_ids"].append(task["task_id"])
        return project

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self.projects.values())
        return [p for p in values if not status or p["status"] == status]

    def get(self, project_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self.projects.get(project_id)

    def advance(self, project_id: str, *, confirm: bool = False, owner_approved: bool = False) -> dict[str, Any]:
        with self._lock:
            project = self.projects.get(project_id)
            if not project:
                return {"status": "not_found", "project_id": project_id}

            if project["approval_required"] and not (owner_approved or project["owner_approved"]):
                project["status"] = "awaiting_owner_approval"
                project["updated_at"] = datetime.now(timezone.utc).isoformat()
                return {"status": project["status"], "project": project}

            if owner_approved:
                project["owner_approved"] = True

            if not confirm:
                return {"status": "awaiting_confirmation", "project": project}

            current = project["status"]
            if current == "planned" or current == "awaiting_owner_approval":
                project["status"] = "executing"
            elif current == "executing":
                project["status"] = "qa"
                project["qa"] = {
                    "status": "ready",
                    "checks": ["scope_review", "task_review", "guardrail_review"],
                }
            elif current == "qa":
                project["status"] = "ready_for_delivery"
            elif current == "ready_for_delivery":
                project["status"] = "delivered"
            else:
                return {"status": "no_transition", "project": project}

            project["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {"status": project["status"], "project": project}

projects = ProjectOps()
