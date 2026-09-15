from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .central_brain import plan

router = APIRouter(prefix="/api/crm", tags=["CRM Sales"])


class SalesIntake(BaseModel):
    lead_id: int
    message: str = Field(min_length=1, max_length=5000)


@router.post("/leads/{lead_id}/route")
def route_lead_to_sales(lead_id: int, payload: SalesIntake):
    if payload.lead_id != lead_id:
        raise HTTPException(status_code=400, detail="lead_id mismatch")

    from .crm import _get
    lead = _get(lead_id)
    decision = plan(payload.message, {"lead_id": lead_id, "company": lead.get("company"), "service": lead.get("service")})

    if decision.requires_owner_approval:
        return {
            "lead": lead,
            "department": decision.department,
            "intent": decision.intent,
            "priority": decision.priority,
            "approval_required": True,
            "executed": False,
            "actions": decision.actions,
            "reason": "Sensitive commitment remains under owner control.",
        }

    return {
        "lead": lead,
        "department": "sales_crm",
        "intent": decision.intent,
        "priority": decision.priority,
        "approval_required": False,
        "executed": True,
        "actions": decision.actions,
        "next_step": "Sales employee may qualify, prepare an offer, and follow up within approved packages.",
    }


@router.get("/sales-queue")
def sales_queue():
    from .main import Entity, engine
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        rows = list(db.scalars(select(Entity).where(Entity.kind == "crm_lead").order_by(Entity.updated_at.desc())))
    return {
        "count": len(rows),
        "queue": [
            {"id": r.id, **r.data, "updated_at": r.updated_at.isoformat()}
            for r in rows
            if r.data.get("stage") not in ("won", "lost")
        ],
    }
