from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/crm", tags=["CRM"])


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: str = "website"
    service: Optional[str] = None
    notes: Optional[str] = None
    value: float = 0
    currency: str = "USD"


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    service: Optional[str] = None
    notes: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    stage: Optional[str] = None
    owner: Optional[str] = None


class StageUpdate(BaseModel):
    stage: str = Field(min_length=1, max_length=60)


STAGES = ("new", "qualified", "proposal", "negotiation", "won", "lost")


def _store(kind: str, data: dict[str, Any], entity_id: Optional[int] = None) -> dict[str, Any]:
    # Import lazily so this module can be installed before main.py creates the FastAPI app.
    from .main import Entity, engine
    from sqlalchemy.orm import Session

    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        if entity_id is None:
            row = Entity(kind=kind, data=data, created_at=now, updated_at=now)
            db.add(row)
        else:
            row = db.get(Entity, entity_id)
            if not row or row.kind != kind:
                raise HTTPException(status_code=404, detail="CRM record not found")
            row.data = data
            row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"id": row.id, "kind": row.kind, **row.data, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


def _get(entity_id: int) -> dict[str, Any]:
    from .main import Entity, engine
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        row = db.get(Entity, entity_id)
        if not row or row.kind != "crm_lead":
            raise HTTPException(status_code=404, detail="CRM lead not found")
        return {"id": row.id, "kind": row.kind, **row.data, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


@router.post("/leads")
def create_lead(payload: LeadCreate):
    data = payload.model_dump()
    data.update({"stage": "new", "owner": "sales", "created_via": "crm"})
    return _store("crm_lead", data)


@router.get("/leads")
def list_leads(stage: Optional[str] = None):
    from .main import Entity, engine
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        rows = list(db.scalars(select(Entity).where(Entity.kind == "crm_lead").order_by(Entity.updated_at.desc())))
    result = [{"id": r.id, "kind": r.kind, **r.data, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()} for r in rows]
    if stage:
        result = [x for x in result if x.get("stage") == stage]
    return {"count": len(result), "stages": list(STAGES), "leads": result}


@router.get("/leads/{lead_id}")
def get_lead(lead_id: int):
    return _get(lead_id)


@router.patch("/leads/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate):
    current = _get(lead_id)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "stage" in updates and updates["stage"] not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid CRM stage")
    current.pop("id", None)
    current.pop("kind", None)
    current.pop("created_at", None)
    current.pop("updated_at", None)
    current.update(updates)
    return _store("crm_lead", current, lead_id)


@router.post("/leads/{lead_id}/stage")
def change_stage(lead_id: int, payload: StageUpdate):
    if payload.stage not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid CRM stage")
    current = _get(lead_id)
    current.pop("id", None)
    current.pop("kind", None)
    current.pop("created_at", None)
    current.pop("updated_at", None)
    current["stage"] = payload.stage
    return _store("crm_lead", current, lead_id)


@router.get("/summary")
def crm_summary():
    from .main import Entity, engine
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        rows = list(db.scalars(select(Entity).where(Entity.kind == "crm_lead")))
    counts = {stage: 0 for stage in STAGES}
    pipeline_value = 0.0
    won_value = 0.0
    for row in rows:
        stage = row.data.get("stage", "new")
        counts[stage] = counts.get(stage, 0) + 1
        value = float(row.data.get("value", 0) or 0)
        if stage not in ("won", "lost"):
            pipeline_value += value
        if stage == "won":
            won_value += value
    return {"total_leads": len(rows), "by_stage": counts, "pipeline_value": pipeline_value, "won_value": won_value, "currency": "USD"}
