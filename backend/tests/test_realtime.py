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


def test_layan_frontend_uses_current_dynamic_voice_ui_and_approved_asset():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    index = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "frontend-v2" / "modules" / "app.js").read_text(encoding="utf-8")
    assert 'layan-realtime-hotfix.js' in index
    assert 'voiceChoice' in app_js
    assert '/assets/layan-office.webp' in app_js
    assert 'id="layanVoiceStage"' in app_js


def test_layan_voice_bridge_supports_browser_speech_fallback():
    from pathlib import Path
    bridge = Path(__file__).resolve().parents[1].parent / 'frontend' / 'layan-realtime-hotfix.js'
    source = bridge.read_text(encoding='utf-8')
    assert 'SpeechRecognition' in source
    assert 'speechSynthesis' in source
    assert 'getUserMedia' in source
    assert 'openLayanVoice' in source


def test_layan_office_asset_is_served_as_webp():
    from app.layan_static import layan_office_asset
    response = layan_office_asset()
    assert response.media_type == 'image/webp'
    assert response.body.startswith(b'RIFF')
    assert response.body[8:12] == b'WEBP'
