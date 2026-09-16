import os
import tempfile

os.environ.setdefault('DATABASE_URL', 'sqlite:///' + tempfile.mktemp(suffix='.db'))
os.environ.setdefault('JWT_SECRET', 'test-secret-key-32-characters-long-123456')
os.environ.setdefault('PASSWORD_PEPPER', 'test-pepper')
os.environ.setdefault('DEMO_ADMIN_PASSWORD', 'change-me')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from app.main import app
from app import realtime_routes

c = TestClient(app)


def test_layan_realtime_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert '/api/voice-avatar/realtime-call' in paths
    assert '/api/voice-avatar/public-session' in paths
    assert realtime_routes.REALTIME_MODEL == 'gpt-realtime-2.1'


def test_layan_instructions_keep_language_and_owner_guardrails():
    text = realtime_routes.LAYAN_INSTRUCTIONS
    assert 'Syrian/Levantine Arabic' in text
    assert 'Egyptian' in text
    assert 'owner approval' in text


def test_layan_realtime_call_rejects_missing_server_configuration():
    old = os.environ.pop('OPENAI_API_KEY', None)
    try:
        r = c.post('/api/voice-avatar/realtime-call', content='v=0\r\n')
        assert r.status_code == 503
    finally:
        if old is not None:
            os.environ['OPENAI_API_KEY'] = old


def test_layan_realtime_call_rejects_empty_sdp():
    os.environ['OPENAI_API_KEY'] = 'test-only-placeholder'
    r = c.post('/api/voice-avatar/realtime-call', content='')
    assert r.status_code == 400
