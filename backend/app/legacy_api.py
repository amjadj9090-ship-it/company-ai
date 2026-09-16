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
