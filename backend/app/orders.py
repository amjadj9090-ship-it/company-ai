from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/api/orders", tags=["Orders"])

STATUSES = ("confirmed", "in_progress", "completed", "cancelled")
PAYMENT_STATUSES = ("unpaid", "pending", "paid", "refunded")


class OrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=40)


class PaymentStatusUpdate(BaseModel):
    payment_status: str = Field(min_length=1, max_length=40)


def _deps():
    from .main import Entity, Session, engine, current_user, allowed
    return Entity, Session, engine, current_user, allowed


def _auth(authorization: Optional[str]):
    Entity, Session, engine, current_user, allowed = _deps()
    with Session(engine) as s:
        u = current_user(authorization, s)
        if not allowed(u, "orders"):
            raise HTTPException(403, "Insufficient permission")
        return u


def _serialize(row):
    return {"id": row.id, **row.data, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


@router.get("")
def list_orders(status: Optional[str] = None, authorization: Optional[str] = Header(None)):
    _auth(authorization)
    Entity, Session, engine, _, _ = _deps()
    with Session(engine) as s:
        rows = list(s.scalars(select(Entity).where(Entity.kind == "orders").order_by(Entity.updated_at.desc())))
    result = [_serialize(r) for r in rows]
    if status:
        result = [r for r in result if r.get("status") == status]
    return {"count": len(result), "statuses": list(STATUSES), "payment_statuses": list(PAYMENT_STATUSES), "orders": result}


@router.get("/{order_id}")
def get_order(order_id: int, authorization: Optional[str] = Header(None)):
    _auth(authorization)
    Entity, Session, engine, _, _ = _deps()
    with Session(engine) as s:
        row = s.get(Entity, order_id)
        if not row or row.kind != "orders":
            raise HTTPException(404, "Order not found")
        return _serialize(row)


@router.patch("/{order_id}/status")
def update_order_status(order_id: int, body: OrderStatusUpdate, authorization: Optional[str] = Header(None)):
    _auth(authorization)
    if body.status not in STATUSES:
        raise HTTPException(400, "Invalid order status")
    Entity, Session, engine, _, _ = _deps()
    with Session(engine) as s:
        row = s.get(Entity, order_id)
        if not row or row.kind != "orders":
            raise HTTPException(404, "Order not found")
        row.data = {**row.data, "status": body.status}
        s.commit()
        s.refresh(row)
        return _serialize(row)


@router.patch("/{order_id}/payment-status")
def update_payment_status(order_id: int, body: PaymentStatusUpdate, authorization: Optional[str] = Header(None)):
    _auth(authorization)
    if body.payment_status not in PAYMENT_STATUSES:
        raise HTTPException(400, "Invalid payment status")
    Entity, Session, engine, _, _ = _deps()
    with Session(engine) as s:
        row = s.get(Entity, order_id)
        if not row or row.kind != "orders":
            raise HTTPException(404, "Order not found")
        row.data = {**row.data, "payment_status": body.payment_status}
        s.commit()
        s.refresh(row)
        return _serialize(row)
