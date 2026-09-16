from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(tags=["Legacy API compatibility"])

def _main():
    from . import main
    return main

def _now():
    return datetime.now(timezone.utc)

def _save(s: Session, kind: str, data: dict):
    main = _main()
    row = main.Entity(kind=kind, data=data, created_at=_now(), updated_at=_now())
    s.add(row)
    s.flush()
    return row

class PublicLead(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    company: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    need: str = Field(min_length=3, max_length=4000)
    source: Optional[str] = "website"
    budget: Optional[str] = None

@router.post("/api/leads/public")
def public_lead(payload: PublicLead):
    main = _main()
    with Session(main.engine) as s:
        row = _save(s, "leads", {"name": payload.name, "email": str(payload.email), "company": payload.company, "country": payload.country, "language": payload.language, "need": payload.need, "source": payload.source, "budget": payload.budget, "stage": "new", "qualified": False})
        s.commit()
        return {"lead_id": row.id, **row.data}

@router.post("/api/leads/{lead_id}/qualify")
def qualify_lead(lead_id: int):
    main = _main()
    with Session(main.engine) as s:
        row = s.get(main.Entity, lead_id)
        if not row or row.kind != "leads":
            raise HTTPException(404, "Lead not found")
        row.data = {**row.data, "qualified": True, "stage": "qualified", "qualified_at": _now().isoformat()}
        row.updated_at = _now()
        s.commit()
        return {"lead_id": row.id, "qualified": True, "stage": "qualified"}

@router.get("/api/growth/funnel")
def growth_funnel():
    main = _main()
    with Session(main.engine) as s:
        rows = list(s.scalars(select(main.Entity).where(main.Entity.kind == "leads")))
    qualified = sum(1 for r in rows if r.data.get("qualified") is True or r.data.get("stage") == "qualified")
    return {"total": len(rows), "qualified": qualified, "stages": {"new": sum(1 for r in rows if r.data.get("stage") == "new"), "qualified": qualified}}

class CentralIntake(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    language: Optional[str] = None
    channel: str = "website"

@router.post("/api/central-ai/intake")
def central_ai_intake(payload: CentralIntake):
    from .central_brain import plan
    decision = plan(payload.message)
    classification = "finance" if decision.department == "finance_legal" else ("web_design" if "website" in payload.message.lower() or "موقع" in payload.message.lower() else decision.intent)
    main = _main()
    data = {"classification": classification, "department": "web_design" if classification == "web_design" else decision.department, "message": payload.message, "language": payload.language, "channel": payload.channel, "human_approval_required": decision.required_approval, "status": "blocked" if decision.required_approval else "planned", "task_id": None}
    with Session(main.engine) as s:
        plan_row = _save(s, "central_plan", data)
        task = _save(s, "task", {"title": f"Central AI: {classification}", "department": data["department"], "status": "blocked" if decision.required_approval else "queued", "source_plan_id": plan_row.id})
        plan_row.data = {**plan_row.data, "task_id": task.id}
        s.commit()
        return {"plan_id": plan_row.id, "task_id": task.id, **plan_row.data}

@router.get("/api/central-ai/plans")
def central_ai_plans():
    main = _main()
    with Session(main.engine) as s:
        rows = list(s.scalars(select(main.Entity).where(main.Entity.kind == "central_plan").order_by(main.Entity.id.desc())))
    return [{"id": r.id, **r.data} for r in rows]

@router.post("/api/central-ai/plans/{plan_id}/advance")
def central_ai_advance(plan_id: int):
    main = _main()
    with Session(main.engine) as s:
        row = s.get(main.Entity, plan_id)
        if not row or row.kind != "central_plan":
            raise HTTPException(404, "Plan not found")
        if row.data.get("human_approval_required"):
            return {"id": row.id, "status": "blocked", **row.data}
        row.data = {**row.data, "status": "advanced"}
        row.updated_at = _now()
        s.commit()
        return {"id": row.id, **row.data}

@router.post("/api/finance/withdraw")
@router.post("/api/finance/transfer")
def blocked_money_operation():
    raise HTTPException(403, "Owner approval is required for company money movement")

@router.get("/api/dashboard/executive")
def executive_dashboard():
    main = _main()
    with Session(main.engine) as s:
        leads = list(s.scalars(select(main.Entity).where(main.Entity.kind.in_(["leads", "crm_lead"]))))
        activities = list(s.scalars(select(main.Entity).order_by(main.Entity.id.desc()).limit(10)))
    qualified = sum(1 for r in leads if r.data.get("qualified") is True or r.data.get("stage") == "qualified")
    return {"lead_pipeline": {"total": len(leads), "qualified": qualified}, "recent_activity": [{"id": r.id, "kind": r.kind, "created_at": r.created_at.isoformat()} for r in activities]}

@router.get("/api/voice-avatar/architecture")
def voice_avatar_architecture():
    return {"ownership": "company_ai", "layers": ["listen", "speech_to_text", "reasoning", "text_to_speech", "avatar"], "models": {"tts": "company-ai-voice-v1"}, "language_policy": "universal", "auto_language_detection": True}
