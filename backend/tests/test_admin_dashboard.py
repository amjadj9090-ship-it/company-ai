import os
import tempfile

os.environ['DATABASE_URL'] = 'sqlite:///' + tempfile.mktemp(suffix='.db')
os.environ['JWT_SECRET'] = 'test-secret-key-32-characters-long-123456'
os.environ['PASSWORD_PEPPER'] = 'test-pepper'
os.environ['DEMO_ADMIN_PASSWORD'] = 'change-me'
os.environ['ENVIRONMENT'] = 'test'

from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def login():
    r = c.post('/api/auth/login', json={'email': 'owner@example.com', 'password': 'change-me'})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}


def test_admin_dashboard_requires_authentication():
    assert c.get('/api/dashboard/summary').status_code in (401, 403)
    assert c.get('/api/admin/leads').status_code in (401, 403)
    assert c.get('/api/approvals').status_code in (401, 403)


def test_admin_dashboard_live_contract():
    h = login()

    dashboard = c.get('/api/dashboard/summary', headers=h)
    assert dashboard.status_code == 200, dashboard.text
    data = dashboard.json()
    assert data['source'] == 'live_database'
    assert set(['conversations_today', 'leads', 'open_opportunities', 'active_agents', 'pending_approvals']).issubset(data['kpis'])
    assert 'central_brain' in data
    assert 'activity' in data
    assert 'updated_at' in data

    for kind in ('leads', 'orders', 'customers', 'products', 'projects'):
        r = c.get(f'/api/admin/{kind}', headers=h)
        assert r.status_code == 200, (kind, r.text)
        assert isinstance(r.json(), list)


def test_admin_approvals_audit_and_ai_decisions_are_protected_and_readable():
    h = login()
    for path in ('/api/approvals', '/api/audit', '/api/ai-decisions'):
        r = c.get(path, headers=h)
        assert r.status_code == 200, (path, r.text)
        assert isinstance(r.json(), list)
