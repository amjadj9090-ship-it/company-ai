from __future__ import annotations
import hashlib,hmac,json,os,secrets,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from typing import Optional
from fastapi import APIRouter,Depends,Header,HTTPException,Request
from pydantic import BaseModel,Field,EmailStr
router=APIRouter(tags=['payments'])

def _main():
    from . import main
    return main

def _now(): return datetime.now(timezone.utc)
def _stripe_key(): return os.getenv('STRIPE_SECRET_KEY','').strip()
def _public_url(): return os.getenv('COMPANY_PUBLIC_URL','https://company-ai-0mya.onrender.com').rstrip('/')
def _session():
    main=_main()
    with main.Session(main.engine) as s: yield s

class CheckoutLinkIn(BaseModel):
    order_id:int
    success_url:Optional[str]=None
    cancel_url:Optional[str]=None
class PublicCheckoutIn(BaseModel):
    payment_token:str=Field(min_length=32,max_length=200)
    customer_email:EmailStr
    success_url:Optional[str]=None
    cancel_url:Optional[str]=None

def _stripe_request(path,fields):
    key=_stripe_key()
    if not key: raise HTTPException(503,'Payment gateway is not configured yet')
    req=urllib.request.Request('https://api.stripe.com/v1/'+path,data=urllib.parse.urlencode(fields).encode(),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/x-www-form-urlencoded','User-Agent':'CompanyAI/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=15) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail=e.read().decode('utf-8','replace')[:1000]
        raise HTTPException(502,'Payment gateway rejected the request: '+detail)
    except Exception: raise HTTPException(502,'Payment gateway is temporarily unavailable')

def _signature_valid(payload,signature,secret):
    try:
        parts={k:v for k,v in (p.split('=',1) for p in signature.split(',') if '=' in p)}
        ts=int(parts.get('t','0'))
        if abs(time.time()-ts)>300:return False
        expected=hmac.new(secret.encode(),f'{ts}.'.encode()+payload,hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,parts.get('v1',''))
    except Exception:return False

@router.get('/api/payments/config')
def payment_config():
    key=_stripe_key()
    return {'provider':'stripe','configured':bool(key),'mode':'live' if key.startswith('sk_live_') else ('test' if key else 'unconfigured'),'currency_default':'usd'}

@router.post('/api/payments/links')
def create_payment_link(x:CheckoutLinkIn,authorization:Optional[str]=Header(None),s=Depends(_session)):
    main=_main(); u=main.current_user(authorization,s)
    if not main.allowed(u,'orders'): raise HTTPException(403,'Insufficient permission')
    order=s.get(main.Entity,x.order_id)
    if not order or order.kind!='orders': raise HTTPException(404,'Order not found')
    if order.data.get('execution_locked') or order.data.get('status') not in ('confirmed','payment_pending'): raise HTTPException(409,'Order is not ready for payment')
    amount=float(order.data.get('total',0))
    if amount<=0: raise HTTPException(400,'Order total must be greater than zero')
    token=secrets.token_urlsafe(36)
    data={'order_id':order.id,'payment_token_hash':hashlib.sha256(token.encode()).hexdigest(),'status':'created','provider':'stripe','currency':str(order.data.get('currency','USD')).lower(),'amount':amount,'created_at':_now().isoformat()}
    p=main.add(s,'payment_sessions',data); order.data={**order.data,'status':'payment_pending','payment_id':p.id}; order.updated_at=_now(); main.audit(s,u,'create_payment_link','payment_sessions',p.id,{'order_id':order.id}); s.commit()
    return {'payment_id':p.id,'payment_token':token,'checkout_endpoint':'/api/payments/checkout','status':'created','provider':'stripe'}

@router.post('/api/payments/checkout')
def public_checkout(x:PublicCheckoutIn,s=Depends(_session)):
    main=_main(); h=hashlib.sha256(x.payment_token.encode()).hexdigest()
    p=s.scalar(main.select(main.Entity).where(main.Entity.kind=='payment_sessions',main.Entity.data['payment_token_hash'].as_string()==h))
    if not p: raise HTTPException(404,'Payment session not found')
    if p.data.get('status') in ('paid','expired','cancelled'): raise HTTPException(409,'Payment session is no longer payable')
    order=s.get(main.Entity,int(p.data.get('order_id')))
    if not order or order.kind!='orders': raise HTTPException(404,'Order not found')
    if order.data.get('execution_locked'): raise HTTPException(403,'Order execution requires owner approval')
    amount=int(round(float(p.data.get('amount',0))*100))
    if amount<=0: raise HTTPException(400,'Invalid payment amount')
    success=x.success_url or (_public_url()+'/?payment=success&token='+urllib.parse.quote(x.payment_token))
    cancel=x.cancel_url or (_public_url()+'/?payment=cancelled&token='+urllib.parse.quote(x.payment_token))
    fields={'mode':'payment','success_url':success,'cancel_url':cancel,'customer_email':str(x.customer_email),'client_reference_id':str(order.id),'metadata[order_id]':str(order.id),'metadata[payment_id]':str(p.id),'line_items[0][price_data][currency]':str(p.data.get('currency','usd')).lower(),'line_items[0][price_data][product_data][name]':'Company AI order #'+str(order.id),'line_items[0][price_data][product_data][description]':'Company AI digital service order','line_items[0][price_data][unit_amount]':str(amount),'line_items[0][quantity]':'1'}
    stripe=_stripe_request('checkout/sessions',fields)
    p.data={**p.data,'stripe_session_id':stripe.get('id'),'status':'checkout_created','customer_email':str(x.customer_email)}; p.updated_at=_now(); order.data={**order.data,'status':'payment_pending','payment_provider':'stripe','stripe_session_id':stripe.get('id')}; order.updated_at=_now(); s.commit()
    return {'payment_id':p.id,'order_id':order.id,'status':'checkout_created','checkout_url':stripe.get('url')}

@router.get('/api/payments/status/{payment_token}')
def payment_status(payment_token:str,s=Depends(_session)):
    main=_main(); h=hashlib.sha256(payment_token.encode()).hexdigest(); p=s.scalar(main.select(main.Entity).where(main.Entity.kind=='payment_sessions',main.Entity.data['payment_token_hash'].as_string()==h))
    if not p: raise HTTPException(404,'Payment session not found')
    return {'payment_id':p.id,'order_id':p.data.get('order_id'),'status':p.data.get('status'),'provider':p.data.get('provider','stripe')}

@router.post('/api/payments/webhook')
async def stripe_webhook(request:Request,stripe_signature:Optional[str]=Header(default=None,alias='Stripe-Signature'),s=Depends(_session)):
    secret=os.getenv('STRIPE_WEBHOOK_SECRET','').strip()
    if not secret: raise HTTPException(503,'Payment webhook is not configured yet')
    payload=await request.body()
    if not stripe_signature or not _signature_valid(payload,stripe_signature,secret): raise HTTPException(400,'Invalid Stripe signature')
    event=json.loads(payload.decode()); typ=event.get('type',''); obj=event.get('data',{}).get('object',{}); meta=obj.get('metadata',{}) or {}; pid=meta.get('payment_id'); oid=meta.get('order_id')
    if not pid or not oid:return {'received':True,'ignored':True}
    main=_main(); p=s.get(main.Entity,int(pid)); order=s.get(main.Entity,int(oid))
    if not p or p.kind!='payment_sessions' or not order or order.kind!='orders':return {'received':True,'ignored':True}
    if typ in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
        p.data={**p.data,'status':'paid','paid_at':_now().isoformat(),'stripe_event':event.get('id')}; order.data={**order.data,'status':'paid','payment_status':'paid','paid_at':_now().isoformat()}
    elif typ in ('checkout.session.async_payment_failed','checkout.session.expired'):
        p.data={**p.data,'status':'failed','stripe_event':event.get('id')}; order.data={**order.data,'status':'payment_failed','payment_status':'failed'}
    else:return {'received':True,'ignored':True}
    p.updated_at=_now(); order.updated_at=_now(); main.audit(s,type('U',(),{'email':'stripe_webhook'})(),'payment_webhook','payment_sessions',p.id,{'event_type':typ,'order_id':order.id}); s.commit(); return {'received':True,'processed':True,'status':p.data.get('status')}
