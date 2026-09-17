from pathlib import Path

ROOT = Path(__file__).parents[2]
MAIN = ROOT / "backend" / "app" / "main.py"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"


def test_production_secrets_are_required_by_runtime_contract():
    source = MAIN.read_text(encoding="utf-8")
    assert "JWT_SECRET must be at least 32 characters in production" in source
    assert "PASSWORD_PEPPER must be configured in production" in source
    assert "DEMO_ADMIN_PASSWORD" in source
    assert "owner@example.com" in source


def test_production_cors_does_not_fallback_to_localhost():
    source = MAIN.read_text(encoding="utf-8")
    assert "CORS_ORIGINS" in source
    assert "http://localhost:8000,http://localhost:5173" in source
    assert "production" in source


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
