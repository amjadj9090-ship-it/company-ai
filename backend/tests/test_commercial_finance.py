from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_standard_package_quote_is_allowed():
    r = client.post('/api/commercial/quotes', json={'lead_id': 1, 'package_id': 'website-starter', 'quantity': 1})
    assert r.status_code == 200
    data = r.json()
    assert data['approval_required'] is False
    assert data['total'] == 500.0


def test_discount_requires_owner_approval():
    r = client.post('/api/commercial/quotes', json={'lead_id': 1, 'package_id': 'website-starter', 'discount_percent': 10})
    assert r.status_code == 200
    data = r.json()
    assert data['approval_required'] is True
    assert data['executed'] is False


def test_money_movement_requires_approval():
    r = client.post('/api/finance/transactions', json={'transaction_type': 'withdrawal', 'amount': 100, 'description': 'test'})
    assert r.status_code == 200
    data = r.json()
    assert data['approval_required'] is True
    assert data['executed'] is False


def test_sensitive_permission_is_blocked():
    r = client.post('/api/permissions/check', json={'action': 'contract_signing', 'standard': True})
    assert r.status_code == 200
    data = r.json()
    assert data['allowed'] is False
    assert data['approval_required'] is True
