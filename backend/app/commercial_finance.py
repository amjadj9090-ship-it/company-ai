from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

router = APIRouter(tags=['commercial-finance'])

PACKAGES = [
    {'id':'website-starter','name':'Website Starter','category':'website','price':500.0,'currency':'USD','pre_approved':True,'description':'Professional business website package.'},
    {'id':'website-pro','name':'Website Pro','category':'website','price':1200.0,'currency':'USD','pre_approved':True,'description':'Advanced business website with lead capture and integrations.'},
    {'id':'app-business','name':'Business App','category':'app','price':2500.0,'currency':'USD','pre_approved':True,'description':'Custom business application package.'},
]

SENSITIVE_ACTIONS = {'money_transfer','money_withdrawal','bank_transfer','bank_withdrawal','contract_signing','nonstandard_discount','nonstandard_commitment','refund','financial_payout'}

class QuoteIn(BaseModel):
    lead_id: int
    package_id: str
    quantity: int = Field(default=1, ge=1, le=100)
    discount_percent: float = Field(default=0, ge=0, le=100)
    notes: Optional[str] = None

class PermissionCheckIn(BaseModel):
    action: Optional[str] = None
    standard: bool = True
    amount: Optional[float] = Field(default=None, ge=0)
    data: Optional[dict] = None

    @model_validator(mode='after')
    def normalize(self):
        if not self.action and isinstance(self.data, dict):
            self.action = str(self.data.get('action', '')).strip() or None
            if 'standard' in self.data:
                self.standard = bool(self.data.get('standard'))
        if not self.action:
            raise ValueError('action is required')
        return self

class TransactionIn(BaseModel):
    transaction_type: str
    amount: float = Field(gt=0)
    currency: str = 'USD'
    description: str = Field(min_length=2, max_length=1000)
    approval_id: Optional[int] = None

def now():
    return datetime.now(timezone.utc)

def package(package_id: str):
    return next((p for p in PACKAGES if p['id'] == package_id), None)

def permission(action: str, standard: bool = True):
    owner = action in SENSITIVE_ACTIONS or not standard
    if owner:
        return {'allowed': True, 'approval_required': True, 'mode': 'owner', 'reason': 'Owner approval is required for sensitive or non-standard commitments.'}
    return {'allowed': True, 'approval_required': False, 'mode': 'auto', 'reason': 'Standard pre-approved action may proceed automatically.'}

def db_models():
    from .main import Session, engine, Entity, Approval
    return Session, engine, Entity, Approval

def save_entity(kind: str, data: dict):
    Session, engine, Entity, _ = db_models()
    with Session(engine) as s:
        item = Entity(kind=kind, data=data, created_at=now(), updated_at=now())
        s.add(item)
        s.commit()
        s.refresh(item)
        return item.id

def approved_owner_action(approval_id: int, action: str):
    Session, engine, _, Approval = db_models()
    with Session(engine) as s:
        approval = s.get(Approval, approval_id)
        if approval is None:
            return False, 'Approval record was not found.'
        if approval.status != 'approved':
            return False, 'Approval record is not approved.'
        if approval.action not in {action, 'financial_payout'}:
            return False, 'Approval action does not authorize this operation.'
        return True, 'Approved by owner.'

@router.get('/api/commercial/packages')
def list_packages():
    return {'packages': PACKAGES}

@router.post('/api/commercial/quotes')
def create_quote(body: QuoteIn):
    p = package(body.package_id)
    if not p:
        raise HTTPException(404, 'Package not found')
    if body.discount_percent > 0:
        check = permission('nonstandard_discount', standard=False)
        return {'status':'approval_required','executed':False,'approval_required':True,'reason':check['reason'],'package':p}
    total = round(p['price'] * body.quantity, 2)
    quote = {'lead_id':body.lead_id,'package_id':p['id'],'title':p['name'],'quantity':body.quantity,'subtotal':total,'discount_percent':0,'total':total,'currency':p['currency'],'notes':body.notes,'status':'prepared','created_at':now().isoformat(),'approval_required':False}
    quote['id'] = save_entity('commercial_quote', quote)
    return quote

@router.get('/api/commercial/quotes')
def list_quotes(lead_id: Optional[int] = None):
    Session, engine, Entity, _ = db_models()
    with Session(engine) as s:
        rows = s.query(Entity).filter(Entity.kind == 'commercial_quote').order_by(Entity.id.desc()).all()
        quotes = [dict(r.data, id=r.id) for r in rows]
    return {'quotes':[q for q in quotes if lead_id is None or q['lead_id']==lead_id]}

@router.post('/api/permissions/check')
def check_permission(body: PermissionCheckIn):
    return {'action':body.action, **permission(body.action, body.standard)}

@router.get('/api/permissions/policy')
def policy():
    return {
        'standard_actions':'AI may execute pre-approved catalog sales and standard service workflows.',
        'owner_only':sorted(SENSITIVE_ACTIONS),
        'rules': {
            'standard_sale': {'allowed': True, 'mode': 'auto'},
            'bank_transfer': {'allowed': True, 'mode': 'owner'},
            'bank_withdrawal': {'allowed': True, 'mode': 'owner'},
        },
        'money_movement':'Never execute without explicit owner approval.',
        'contract_signing':'Never execute without explicit owner approval.'
    }

@router.post('/api/finance/transactions')
def create_transaction(body: TransactionIn):
    if body.approval_id is None:
        return {'status':'approval_required','executed':False,'approval_required':True,'reason':'Money movement is owner-controlled; an approved approval_id is required.'}
    ok, reason = approved_owner_action(body.approval_id, body.transaction_type)
    if not ok:
        return {'status':'approval_required','executed':False,'approval_required':True,'reason':reason}
    tx = {'type':body.transaction_type,'amount':body.amount,'currency':body.currency,'description':body.description,'approval_id':body.approval_id,'status':'approved_pending_execution','created_at':now().isoformat()}
    tx['id'] = save_entity('financial_transaction', tx)
    return tx

@router.get('/api/finance/summary')
def finance_summary():
    Session, engine, Entity, _ = db_models()
    with Session(engine) as s:
        rows = s.query(Entity).filter(Entity.kind == 'financial_transaction').all()
        approved = [r.data for r in rows if r.data.get('status') == 'approved_pending_execution']
    approved_total = sum(x.get('amount', 0) for x in approved)
    return {'currency':'USD','pending_approved_transactions':len(approved),'pending_approved_amount':round(approved_total,2),'execution_policy':'owner approval required'}
