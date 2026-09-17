import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
MAIN = ROOT / "backend" / "app" / "main.py"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"


def _import_main(env):
    cmd = [sys.executable, "-c", "import backend.app.main"]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)


def test_production_rejects_default_or_missing_secret_material(tmp_path):
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "ENVIRONMENT": "production",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'reject.db'}",
        "JWT_SECRET": "x" * 32,
        "PASSWORD_PEPPER": "safe-pepper-value-123456",
        "DEMO_ADMIN_PASSWORD": "change-me",
        "COMPANY_OWNER_EMAIL": "owner@example.com",
    })
    result = _import_main(env)
    assert result.returncode != 0
    assert "DEMO_ADMIN_PASSWORD" in result.stderr


def test_production_starts_with_explicit_secret_material(tmp_path):
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "ENVIRONMENT": "production",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'valid.db'}",
        "JWT_SECRET": "x" * 32,
        "PASSWORD_PEPPER": "safe-pepper-value-123456",
        "DEMO_ADMIN_PASSWORD": "safe-admin-password-123",
        "COMPANY_OWNER_EMAIL": "owner@company-ai.example",
        "CORS_ORIGINS": "https://company-ai.example",
    })
    result = _import_main(env)
    assert result.returncode == 0, result.stderr


def test_production_cors_does_not_fallback_to_localhost():
    source = MAIN.read_text(encoding="utf-8")
    assert "default_origins='' if ENVIRONMENT=='production'" in source
    assert "CORS_ORIGINS" in source
    assert "http://localhost:8000,http://localhost:5173" in source


def test_security_headers_and_transport_controls_are_present():
    source = MAIN.read_text(encoding="utf-8")
    for header in (
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Content-Security-Policy",
        "Strict-Transport-Security",
    ):
        assert header in source
    assert "HTTPSRedirectMiddleware" in source
    assert "Request too large" in source
    assert "Rate limit exceeded" in source


def test_production_api_documentation_is_disabled():
    source = MAIN.read_text(encoding="utf-8")
    assert "docs_url=None if os.getenv('ENVIRONMENT')=='production'" in source
    assert "redoc_url=None if os.getenv('ENVIRONMENT')=='production'" in source
    assert "openapi_url=None if os.getenv('ENVIRONMENT')=='production'" in source


def test_env_example_contains_no_real_secret_material():
    env = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "CHANGE_ME" in env
    assert "GENERATE_A_LONG_RANDOM_SECRET" in env
    assert "GENERATE_A_LONG_RANDOM_PEPPER" in env
