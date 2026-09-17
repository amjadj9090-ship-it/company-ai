from datetime import datetime, timezone
import secrets
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/public-lifecycle", tags=["public-customer-lifecycle"])


def _main():
    # Import lazily so app/__init__.py can register this router while
    # app.main is still being constructed, avoiding a circular import.
    from . import main
    return main


def db():
    main = _main()
    s = main.Session(main.engine)
    try:
        yield s
    finally:
        s.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def add(s, kind, data):
    main = _main()
    timestamp = datetime.now(timezone.utc)
    e = main.Entity(kind=kind, data=data, created_at=timestamp, updated_at=timestamp)
    s.add(e)
    s.flush()
    return e


class ProposalView(BaseModel):
    token: str


class Accept(BaseModel):
    token: str
    customer_note: str | None = None


class Order(BaseModel):
    token: str


def _token_record(s, token):
    main = _main()
    records = s.scalars(select(main.Entity).where(main.Entity.kind == "customer_proposal_tokens")).all()
    return next((z for z in records if z.data.get("token") == token and not z.data.get("used")), None)


def _proposal(s, rec):
    main = _main()
    if not rec:
        raise HTTPException(404, "Invalid proposal token")
    p = s.get(main.Entity, rec.data.get("proposal_id"))
    if not p or p.kind != "proposals":
        raise HTTPException(404, "Proposal not found")
    return p


@router.post("/proposal/view")
def proposal_view(x: ProposalView, s: Session = Depends(db)):
    rec = _token_record(s, x.token)
    p = _proposal(s, rec)
    return {"id": p.id, **p.data, "customer_token": x.token}


@router.post("/proposal/accept")
def proposal_accept(x: Accept, s: Session = Depends(db)):
    rec = _token_record(s, x.token)
    p = _proposal(s, rec)
    if p.data.get("status") not in ("draft", "sent"):
        raise HTTPException(409, "Proposal cannot be accepted")
    p.data = {**p.data, "status": "accepted_by_customer", "customer_note": x.customer_note, "accepted_at": now()}
    s.commit()
    return {"proposal_id": p.id, "status": p.data["status"]}


@router.post("/proposal/order")
def proposal_order(x: Order, s: Session = Depends(db)):
    rec = _token_record(s, x.token)
    p = _proposal(s, rec)
    if p.data.get("status") != "accepted_by_customer":
        raise HTTPException(409, "Customer acceptance is required")
    main = _main()
    existing = s.scalars(select(main.Entity).where(main.Entity.kind == "orders")).all()
    found = next((o for o in existing if o.data.get("proposal_id") == p.id), None)
    if found:
        return {"id": found.id, **found.data}
    order = add(s, "orders", {
        "proposal_id": p.id,
        "lead_id": p.data.get("lead_id"),
        "status": "confirmed",
        "payment_status": "unpaid",
        "execution_locked": bool(p.data.get("human_approval_required")),
    })
    rec.data = {**rec.data, "used": True, "used_at": now()}
    s.commit()
    return {"id": order.id, **order.data}


@router.post("/proposal/token")
def proposal_token(proposal_id: int, s: Session = Depends(db), authorization: str | None = Header(None)):
    main = _main()
    u = main.current_user(authorization, s)
    if not main.allowed(u, "proposals"):
        raise HTTPException(403, "Insufficient permission")
    p = s.get(main.Entity, proposal_id)
    if not p or p.kind != "proposals":
        raise HTTPException(404, "Proposal not found")
    token = secrets.token_urlsafe(32)
    add(s, "customer_proposal_tokens", {"proposal_id": proposal_id, "token": token, "used": False, "created_at": now()})
    s.commit()
    return {"proposal_id": proposal_id, "token": token}
