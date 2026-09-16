from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
router = APIRouter(tags=["Admin compatibility"])

def _deps():
    from .main import Entity, Audit, Approval, current_user
    return Entity, Audit, Approval, current_user

def _db():
    from .main import engine
    return Session(engine)

def _admin_user():
    *_, current_user = _deps()
    return current_user

@router.get("/api/admin/{kind}")
def admin_list(kind: str, u=Depends(_admin_user)):
    Entity, _, _, _ = _deps()
    allowed_kinds = {
        "leads": "crm_lead", "customers": "customer", "proposals": "proposal", "orders": "order", "invoices": "invoice", "projects": "project", "tasks": "task", "products": "product", "contracts": "contract", "tickets": "ticket", "suppliers": "supplier", "campaigns": "campaign", "partners": "partner", "content": "content", "marketplace": "marketplace", "feasibility_studies": "feasibility_study", "website_assessments": "website_assessment", "security_assessments": "security_assessment", "security_incidents": "security_incident", "monitoring_incidents": "monitoring_incident", "agent_builds": "agent_build", "voice_profiles": "voice_profile", "avatar_profiles": "avatar_profile", "voice_sessions": "voice_session", "avatar_jobs": "avatar_job", "speech_models": "speech_model",
    }
    entity_kind = allowed_kinds.get(kind, kind)
    with _db() as s:
        rows = list(s.scalars(select(Entity).where(Entity.kind == entity_kind).order_by(Entity.id.desc())))
    return [dict(r.data, id=r.id, created_at=r.created_at.isoformat(), updated_at=r.updated_at.isoformat()) for r in rows]

@router.get("/api/approvals")
def admin_approvals(u=Depends(_admin_user)):
    _, _, Approval, _ = _deps()
    with _db() as s:
        rows = list(s.scalars(select(Approval).order_by(Approval.id.desc())))
    return [{"id": r.id, "action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id, "reason": r.reason, "status": r.status, "requested_by": r.requested_by, "decided_by": r.decided_by, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()} for r in rows]

@router.get("/api/audit")
def admin_audit(u=Depends(_admin_user)):
    _, Audit, _, _ = _deps()
    with _db() as s:
        rows = list(s.scalars(select(Audit).order_by(Audit.id.desc()).limit(200)))
    return [{"id": r.id, "actor": r.actor, "action": r.action, "entity": r.entity, "entity_id": r.entity_id, "details": r.details, "created_at": r.created_at.isoformat()} for r in rows]

@router.get("/api/ai-decisions")
def admin_ai_decisions(u=Depends(_admin_user)):
    Entity, _, _, _ = _deps()
    with _db() as s:
        rows = list(s.scalars(select(Entity).where(Entity.kind.in_(["ai_decision", "central_ai_decision", "ai_decisions"])).order_by(Entity.id.desc()).limit(200)))
    return [dict(r.data, id=r.id, kind=r.kind, created_at=r.created_at.isoformat(), updated_at=r.updated_at.isoformat()) for r in rows]
