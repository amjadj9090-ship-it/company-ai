from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=['commercial-finance'])

PACKAGES = [
    {'id':'website-starter','name':'Website Starter','category':'website','price':500.0,'currency':'USD','pre_approved':True,'description':'Professional business website package.'},
    {'id':'website-pro','name':'Website Pro','category':'website','price':1200.0,'currency':'USD','pre_approved':True,'description':'Advanced business website with lead capture and integrations.'},
    {'id':'app-business','name':'Business App','category':'app','price':2500.0,'currency':'USD','pre_approved':True,'description':'Custom business application package.'},
]

SENSITIVE_ACTIONS = {'money_transfer','money_withdrawal','contract_signing','nonstandard_discount','nonstandard_commitment','refund','financial_payout'}

class QuoteIn(BaseModel):
    lead_id: int
    package_id: str
    quantity: int = Field(default=1, ge=1, le=100)
    discount_percent: float = Field(default=0, ge=0, le=100)
    notes: Optional[str] = None

class PermissionCheckIn(BaseModel):
    action: str
    standard: bool = True
    amount: Optional[float] = Field(default=None, ge=0)

class TransactionIn(BaseModel):
    transaction_type: str
    amount: float = Field(gt=0)
    currency: str = 'USD'
    description: str = Field(min_length=2, max_length=1000)
    approval_id: Optional[int] = None

_quotes: list[dict] = []
_transactions: list[dict] = []

def now():
    return datetime.now(timezone.utc).isoformat()

def package(package_id: str):
    return next((p for p in PACKAGES if p['id'] == package_id), None)

def permission(action: str, standard: bool = True):
    if action in SENSITIVE_ACTIONS or not standard:
        return {'allowed': False, 'approval_required': True, 'reason': 'Owner approval is required for sensitive or non-standard commitments.'}
    return {'allowed': True, 'approval_required': False, 'reason': 'Standard pre-approved action may proceed automatically.'}

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
    quote = {'id':len(_quotes)+1,'lead_id':body.lead_id,'package_id':p['id'],'title':p['name'],'quantity':body.quantity,'subtotal':total,'discount_percent':0,'total':total,'currency':p['currency'],'notes':body.notes,'status':'prepared','created_at':now(),'approval_required':False}
    _quotes.append(quote)
    return quote

@router.get('/api/commercial/quotes')
def list_quotes(lead_id: Optional[int] = None):
    return {'quotes':[q for q in _quotes if lead_id is None or q['lead_id']==lead_id]}

@router.post('/api/permissions/check')
def check_permission(body: PermissionCheckIn):
    return {'action':body.action, **permission(body.action, body.standard)}

@router.get('/api/permissions/policy')
def policy():
    return {'standard_actions':'AI may execute pre-approved catalog sales and standard service workflows.','owner_only':sorted(SENSITIVE_ACTIONS),'money_movement':'Never execute without explicit owner approval.','contract_signing':'Never execute without explicit owner approval.'}

@router.post('/api/finance/transactions')
def create_transaction(body: TransactionIn):
    if body.approval_id is None:
        return {'status':'approval_required','executed':False,'approval_required':True,'reason':'Money movement is owner-controlled; an approved approval_id is required.'}
    tx={'id':len(_transactions)+1,'type':body.transaction_type,'amount':body.amount,'currency':body.currency,'description':body.description,'approval_id':body.approval_id,'status':'approved_pending_execution','created_at':now()}
    _transactions.append(tx)
    return tx

@router.get('/api/finance/summary')
def finance_summary():
    approved_total = sum(x['amount'] for x in _transactions if x['status']=='approved_pending_execution')
    return {'currency':'USD','pending_approved_transactions':len(_transactions),'pending_approved_amount':round(approved_total,2),'execution_policy':'owner approval required'}
