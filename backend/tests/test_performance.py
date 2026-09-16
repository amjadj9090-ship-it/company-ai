from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_performance_contracts_are_present():
    source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "pool_pre_ping=True" in source
    assert "MAX_REQUEST_BYTES" in source
    assert "PUBLIC_RATE_LIMIT" in source
    assert "Rate limit exceeded" in source
    assert "docs_url=None if os.getenv('ENVIRONMENT')=='production'" in source


def test_frontend_pages_have_mobile_viewport_contract():
    frontend = ROOT / "frontend"
    for name in ("index.html", "admin.html", "dashboard.html"):
        html = (frontend / name).read_text(encoding="utf-8")
        assert "width=device-width" in html
        assert "initial-scale=1" in html
