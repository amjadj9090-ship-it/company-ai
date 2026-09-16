import os
import tempfile

os.environ.setdefault('DATABASE_URL', 'sqlite:///' + tempfile.mktemp(suffix='.db'))
os.environ.setdefault('JWT_SECRET', 'test-secret-key-32-characters-long-123456')
os.environ.setdefault('PASSWORD_PEPPER', 'test-pepper')
os.environ.setdefault('DEMO_ADMIN_PASSWORD', 'change-me')
os.environ.setdefault('ENVIRONMENT', 'test')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_http_errors_have_stable_shape_and_request_id():
    response = client.get('/api/me')
    assert response.status_code == 401
    assert response.headers.get('X-Request-ID')
    body = response.json()
    assert body['error_code'] == 'HTTP_ERROR'
    assert body['request_id'] == response.headers['X-Request-ID']
    assert body['detail'] == 'Authentication required'


def test_validation_errors_have_stable_shape_and_request_id():
    response = client.post('/api/auth/login', json={})
    assert response.status_code == 422
    assert response.headers.get('X-Request-ID')
    body = response.json()
    assert body['error_code'] == 'VALIDATION_ERROR'
    assert body['request_id'] == response.headers['X-Request-ID']
    assert isinstance(body['detail'], list)
