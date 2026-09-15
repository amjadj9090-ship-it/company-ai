from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr

router = APIRouter(tags=['payments'])


def _main():
    from . import main
    return main


def _now():
    return datetime.now(timezone.utc)


def _stripe_key() -> str:
    return os.getenv('STRIPE_SECRET_KEY', '').strip()


def _public_url() -> str:
    return os.getenv('COMPANY_PUBLIC_URL', 'https://company-ai-0mya.onrender.com').rstrip('/')


class CheckoutLinkIn(BaseModel):
    order_id: int
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PublicCheckoutIn(BaseModel):
    payment_token: str = Field(min_length=32, max_length=200)
    customer_email: EmailStr
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentStatusIn(BaseModel):
    payment_token: str = Field(min_length=32, max_length=200)


def _stripe_request(path: str, fields: dict) -> dict:
    key = _stripe_key()
    if not key:
        raise HTTPException(503, 'Payment gateway is not configured yet')
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        'https://api.stripe.com/v1/' + path,
        data=body,
        method='POST',
        headers={
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'CompanyAI/1.0',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:1000]
        raise HTTPException(502, 'Payment gateway rejected the request: ' + detail)
    except Exception:
        raise HTTPException(502, 'Payment gateway is temporarily unavailable')


def _stripe_signature_valid(payload: bytes, signature: str, secret: str) -> bool:
    try:
        parts = dict(item.split('=', 1) for item in signature.split(',') if '=' in item)
        timestamp = int(parts.get('t', '0'))
        if abs(time.time() - timestamp) > 300:
            return False
        signed = f'{timestamp}.'.encode() + payload
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, parts.get('v1', ''))
    except Exception:
        return False


@router.get('/api/payments/config')
def payment_config():
    return {
        'provider': 'stripe',
        'configured': bool(_stripe_key()),
        'mode': 'live' if _stripe_key().startswith('sk_live_') else ('test' if _stripe_key() else 'unconfigured'),
        'currency_default': 'usd',
    }


@router.post('/api/payments/links')
def create_payment_link(x: CheckoutLinkIn, u=Depends(lambda: _main().current_user()), s=Depends(lambda: _main().db())):
    main = _main()
    # Resolve generator dependency manually because this module is installed before main finishes importing.
    session = next(s)
    try:
        if not main.allowed(u, 'orders'):
            raise HTTPException(403, 'Insufficient permission')
        order = session.get(main.Entity, x.order_id)
        if not order or order.kind != 'orders':
            raise HTTPException(404, 'Order not found')
        if order.data.get('execution_locked') or order.data.get('status') not in ('confirmed', 'payment_pending'):
            raise HTTPException(409, 'Order is not ready for payment')
        if float(order.data.get('total', 0)) <= 0:
            raise HTTPException(400, 'Order total must be greater than zero')
        token = secrets.token_urlsafe(36)
        data = {
            'order_id': order.id,
            'payment_token_hash': hashlib.sha256(token.encode()).hexdigest(),
            'status': 'created',
            'provider': 'stripe',
            'currency': str(order.data.get('currency', 'USD')).lower(),
            'amount': float(order.data.get('total', 0)),
            'created_at': _now().isoformat(),
        }
        payment = main.add(session, 'payment_sessions', data)
        order.data = {**order.data, 'status': 'payment_pending', 'payment_id': payment.id}
        order.updated_at = _now()
        main.audit(session, u, 'create_payment_link', 'payment_sessions', payment.id, {'order_id': order.id})
        session.commit()
        return {
            'payment_id': payment.id,
            'payment_token': token,
            'checkout_endpoint': '/api/payments/checkout',
            'status': 'created',
            'provider': 'stripe',
        }
    finally:
        session.close()


@router.post('/api/payments/checkout')
def public_checkout(x: PublicCheckoutIn, s=Depends(lambda: _main().db())):
    main = _main()
    session = next(s)
    try:
        token_hash = hashlib.sha256(x.payment_token.encode()).hexdigest()
        payment = session.scalar(main.select(main.Entity).where(
            main.Entity.kind == 'payment_sessions',
            main.Entity.data['payment_token_hash'].as_string() == token_hash,
        ))
        if not payment:
            raise HTTPException(404, 'Payment session not found')
        if payment.data.get('status') in ('paid', 'expired', 'cancelled'):
            raise HTTPException(409, 'Payment session is no longer payable')
        order = session.get(main.Entity, int(payment.data.get('order_id')))
        if not order or order.kind != 'orders':
            raise HTTPException(404, 'Order not found')
        if order.data.get('execution_locked'):
            raise HTTPException(403, 'Order execution requires owner approval')
        amount = int(round(float(payment.data.get('amount', 0)) * 100))
        if amount <= 0:
            raise HTTPException(400, 'Invalid payment amount')
        success = x.success_url or (_public_url() + '/?payment=success&token=' + urllib.parse.quote(x.payment_token))
        cancel = x.cancel_url or (_public_url() + '/?payment=cancelled&token=' + urllib.parse.quote(x.payment_token))
        fields = {
            'mode': 'payment',
            'success_url': success,
            'cancel_url': cancel,
            'customer_email': str(x.customer_email),
            'client_reference_id': str(order.id),
            'metadata[order_id]': str(order.id),
            'metadata[payment_id]': str(payment.id),
            'line_items[0][price_data][currency]': str(payment.data.get('currency', 'usd')).lower(),
            'line_items[0][price_data][product_data][name]': 'Company AI order #' + str(order.id),
            'line_items[0][price_data][product_data][description]': 'Company AI digital service order',
            'line_items[0][price_data][unit_amount]': str(amount),
            'line_items[0][quantity]': '1',
        }
        stripe = _stripe_request('checkout/sessions', fields)
        payment.data = {**payment.data, 'stripe_session_id': stripe.get('id'), 'status': 'checkout_created', 'customer_email': str(x.customer_email)}
        payment.updated_at = _now()
        order.data = {**order.data, 'status': 'payment_pending', 'payment_provider': 'stripe', 'stripe_session_id': stripe.get('id')}
        order.updated_at = _now()
        session.commit()
        return {'payment_id': payment.id, 'order_id': order.id, 'status': 'checkout_created', 'checkout_url': stripe.get('url')}
    finally:
        session.close()


@router.get('/api/payments/status/{payment_token}')
def payment_status(payment_token: str, s=Depends(lambda: _main().db())):
    main = _main()
    session = next(s)
    try:
        token_hash = hashlib.sha256(payment_token.encode()).hexdigest()
        payment = session.scalar(main.select(main.Entity).where(
            main.Entity.kind == 'payment_sessions',
            main.Entity.data['payment_token_hash'].as_string() == token_hash,
        ))
        if not payment:
            raise HTTPException(404, 'Payment session not found')
        return {'payment_id': payment.id, 'order_id': payment.data.get('order_id'), 'status': payment.data.get('status'), 'provider': payment.data.get('provider', 'stripe')}
    finally:
        session.close()


@router.post('/api/payments/webhook')
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(default=None, alias='Stripe-Signature')):
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
    if not secret:
        raise HTTPException(503, 'Payment webhook is not configured yet')
    payload = await request.body()
    if not stripe_signature or not _stripe_signature_valid(payload, stripe_signature, secret):
        raise HTTPException(400, 'Invalid Stripe signature')
    event = json.loads(payload.decode('utf-8'))
    event_type = event.get('type', '')
    obj = event.get('data', {}).get('object', {})
    metadata = obj.get('metadata', {}) or {}
    payment_id = metadata.get('payment_id')
    order_id = metadata.get('order_id')
    if not payment_id or not order_id:
        return {'received': True, 'ignored': True}
    main = _main()
    session = next(main.db())
    try:
        payment = session.get(main.Entity, int(payment_id))
        order = session.get(main.Entity, int(order_id))
        if not payment or payment.kind != 'payment_sessions' or not order or order.kind != 'orders':
            return {'received': True, 'ignored': True}
        if event_type in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
            payment.data = {**payment.data, 'status': 'paid', 'paid_at': _now().isoformat(), 'stripe_event': event.get('id')}
            order.data = {**order.data, 'status': 'paid', 'payment_status': 'paid', 'paid_at': _now().isoformat()}
        elif event_type in ('checkout.session.async_payment_failed', 'checkout.session.expired'):
            payment.data = {**payment.data, 'status': 'failed', 'stripe_event': event.get('id')}
            order.data = {**order.data, 'status': 'payment_failed', 'payment_status': 'failed'}
        else:
            return {'received': True, 'ignored': True}
        payment.updated_at = _now(); order.updated_at = _now()
        main.audit(session, type('U', (), {'email': 'stripe_webhook'})(), 'payment_webhook', 'payment_sessions', payment.id, {'event_type': event_type, 'order_id': order.id})
        session.commit()
        return {'received': True, 'processed': True, 'status': payment.data.get('status')}
    finally:
        session.close()
