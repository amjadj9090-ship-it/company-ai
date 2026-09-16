import os
import tempfile

os.environ.setdefault('DATABASE_URL', 'sqlite:///' + tempfile.mktemp(suffix='.db'))
os.environ.setdefault('JWT_SECRET', 'test-secret-key-32-characters-long-123456')
os.environ.setdefault('PASSWORD_PEPPER', 'test-pepper')
os.environ.setdefault('DEMO_ADMIN_PASSWORD', 'change-me')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def login():
    r = c.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'change-me'})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}


def test_order_routes_are_registered_and_protected():
    paths = {route.path for route in app.routes}
    assert '/api/orders' in paths
    assert '/api/orders/{order_id}' in paths
    assert '/api/orders/{order_id}/status' in paths
    assert '/api/orders/{order_id}/payment-status' in paths
    assert c.get('/api/orders').status_code in (401, 403)


def test_order_lifecycle_status_and_payment_updates():
    h = login()
    from app import main
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    s = main.Session(main.engine)
    try:
        row = main.Entity(kind='orders', data={'status': 'confirmed', 'payment_status': 'unpaid', 'proposal_id': 1}, created_at=now, updated_at=now)
        s.add(row)
        s.commit()
        s.refresh(row)
        order_id = row.id
    finally:
        s.close()

    r = c.get('/api/orders', headers=h)
    assert r.status_code == 200
    assert any(x['id'] == order_id for x in r.json()['orders'])

    r = c.patch(f'/api/orders/{order_id}/status', headers=h, json={'status': 'in_progress'})
    assert r.status_code == 200
    assert r.json()['status'] == 'in_progress'

    r = c.patch(f'/api/orders/{order_id}/payment-status', headers=h, json={'payment_status': 'paid'})
    assert r.status_code == 200
    assert r.json()['payment_status'] == 'paid'


def test_order_status_validation():
    h = login()
    r = c.patch('/api/orders/999999/status', headers=h, json={'status': 'not-a-status'})
    assert r.status_code == 400
