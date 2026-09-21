import os
import tempfile

os.environ['DATABASE_URL'] = 'sqlite:///' + tempfile.mktemp(suffix='.db')
os.environ['JWT_SECRET'] = 'test-secret-key-32-characters-long-123456'
os.environ['PASSWORD_PEPPER'] = 'test-pepper'
os.environ['DEMO_ADMIN_PASSWORD'] = 'change-me'
os.environ['ENVIRONMENT'] = 'test'

from fastapi.testclient import TestClient
from app.main import app, permission_decision

c = TestClient(app)


def login():
    r = c.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'change-me'})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}


def test_health_and_security_headers():
    r = c.get('/healthz')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert r.headers['x-frame-options'] == 'DENY'
    assert 'default-src' in r.headers['content-security-policy']


def test_auth_and_summary_contract():
    h = login()
    assert c.get('/api/me', headers=h).status_code == 200
    assert c.get('/api/summary', headers=h).status_code == 200


def test_crm_lead_create_update_and_summary_contract():
    r = c.post('/api/crm/leads', json={'name': 'Contract Client', 'email': 'contract@example.com', 'company': 'Contract Co', 'value': 1200})
    assert r.status_code == 200, r.text
    lead_id = r.json()['id']
    r = c.patch(f'/api/crm/leads/{lead_id}', json={'stage': 'qualified'})
    assert r.status_code == 200, r.text
    assert r.json()['stage'] == 'qualified'
    summary = c.get('/api/crm/summary')
    assert summary.status_code == 200
    assert summary.json()['by_stage']['qualified'] >= 1


def test_central_brain_current_contract():
    r = c.post('/api/brain/plan', json={'message': 'I need a company website', 'language': 'en'})
    assert r.status_code == 200
    d = r.json()['decision']
    assert d['department'] == 'digital_services'
    assert d['approval_mode'] == 'auto_standard'
    assert d['required_approval'] is False


def test_central_brain_sensitive_request_is_owner_gated():
    r = c.post('/api/brain/plan', json={'message': 'I need to transfer company money', 'language': 'en'})
    assert r.status_code == 200
    d = r.json()['decision']
    assert d['department'] == 'finance_legal'
    assert d['approval_mode'] == 'owner'
    assert d['required_approval'] is True


def test_permission_contract():
    h = login()
    r = c.post('/api/permissions/check', headers=h, json={'data': {'action': 'standard_sale'}})
    assert r.status_code == 200
    assert r.json()['allowed'] is True
    assert r.json()['mode'] == 'auto'
    r = c.post('/api/permissions/check', headers=h, json={'data': {'action': 'bank_withdrawal'}})
    assert r.status_code == 200
    assert r.json()['allowed'] is True
    assert r.json()['mode'] == 'owner'
    policy = c.get('/api/permissions/policy', headers=h)
    assert policy.status_code == 200
    assert policy.json()['rules']['bank_withdrawal']['mode'] == 'owner'


def test_staff_permission_engine():
    class Staff:
        email = 'staff@example.com'
        role = 'sales'
    assert permission_decision(Staff(), 'bank_withdrawal')['allowed'] is False
    assert permission_decision(Staff(), 'standard_sale')['allowed'] is True


def test_commercial_packages_and_quotes():
    packages = c.get('/api/commercial/packages')
    assert packages.status_code == 200
    assert any(p['id'] == 'website-starter' for p in packages.json()['packages'])
    r = c.post('/api/commercial/quotes', json={'lead_id': 1, 'package_id': 'website-starter'})
    assert r.status_code == 200
    assert r.json()['total'] == 500
    assert r.json()['approval_required'] is False


def test_nonstandard_discount_stays_approval_required():
    r = c.post('/api/commercial/quotes', json={'lead_id': 1, 'package_id': 'website-starter', 'discount_percent': 10})
    assert r.status_code == 200
    assert r.json()['approval_required'] is True
    assert r.json()['executed'] is False


def test_finance_boundary_uses_approval_transaction_api():
    h = login()
    r = c.post('/api/finance/transactions', headers=h, json={'transaction_type': 'bank_withdrawal', 'amount': 100, 'description': 'test'})
    assert r.status_code == 200
    assert r.json()['approval_required'] is True
    assert r.json()['executed'] is False
    assert c.post('/api/finance/withdraw', headers=h, json={'amount': 100}).status_code == 404


def test_agent_builder_and_sales_contract():
    h = login()
    r = c.post('/api/agent-builder/builds', headers=h, json={
        'name': 'Contract Sales Agent', 'role': 'sales', 'purpose': 'Qualify leads',
        'channels': ['website'], 'languages': ['ar', 'en'],
    })
    assert r.status_code == 200, r.text
    aid = r.json()['id']
    t = c.post(f'/api/agent-builder/builds/{aid}/test', headers=h, json={'message': 'I need a website'})
    assert t.status_code == 200
    assert t.json()['status'] == 'passed'
    assert c.get(f'/api/sales-agent/{aid}/operations').status_code == 200


def test_public_sales_agent_contract():
    cfg = c.get('/api/sales-agent/public/config')
    assert cfg.status_code == 200
    aid = cfg.json()['build_id']
    r = c.post(f'/api/sales-agent/{aid}/conversation', json={'message': 'I need a website', 'language': 'en'})
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'
    assert r.json()['recommendations']


def test_public_customer_lifecycle_router_contract():
    paths = {route.path for route in app.routes}
    assert '/api/public-lifecycle/proposal/view' in paths
    assert '/api/public-lifecycle/proposal/accept' in paths
    assert '/api/public-lifecycle/proposal/order' in paths
    assert '/api/public-lifecycle/proposal/token' in paths


def test_payment_configuration_contract():
    r = c.get('/api/payments/config')
    assert r.status_code == 200
    assert r.json()['provider'] == 'stripe'
    assert 'configured' in r.json()


def test_layan_public_session_is_deterministic_in_ci():
    r = c.post('/api/voice-avatar/public-session')
    assert r.status_code == 200
    d = r.json()
    assert d['public'] is True
    assert d['engine'] == 'company-ai-native'
    assert d['avatar_id'] == 'layan'


def test_admin_page_not_public_in_test_environment():
    assert c.get('/admin.html').status_code == 404


def test_dashboard_contract_is_summary_not_legacy_executive_route():
    assert c.get('/dashboard').status_code == 200
    h = login()
    r = c.get('/api/dashboard/summary', headers=h)
    assert r.status_code == 200
    assert r.json()['source'] == 'live_database'


def test_current_api_has_no_removed_legacy_contracts():
    paths = {route.path for route in app.routes}
    assert '/api/central-ai/intake' in paths
    assert '/api/finance/withdraw' not in paths
    assert '/api/dashboard/executive' not in paths
    assert '/api/voice-avatar/architecture' not in paths
