from pathlib import Path

ROOT = Path(__file__).parents[2]
FRONTEND = ROOT / "frontend"
FRONTEND_V2 = ROOT / "frontend-v2"


def read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_public_and_admin_pages_are_mobile_ready():
    index = read("index.html")
    assert 'meta name="viewport"' in index
    for name in ("admin.html", "dashboard.html"):
        html = read(name)
        assert '<meta name="viewport" content="width=device-width,initial-scale=1">' in html
        assert 'lang="ar"' in html
        assert 'dir="rtl"' in html


def test_current_public_mobile_layout_contracts_exist():
    app_js = (FRONTEND_V2 / "modules" / "app.js").read_text(encoding="utf-8")
    css = (FRONTEND_V2 / "styles" / "base.css").read_text(encoding="utf-8")
    assert "voiceChoice" in app_js
    assert "/assets/layan-office.webp" in app_js
    assert "@media(max-width:680px)" in css or "@media (max-width:680px)" in css


def test_admin_and_dashboard_mobile_overflow_protection_remains():
    admin = read("admin.html")
    dashboard = read("dashboard.html")
    assert "overflow-x:hidden" in admin or "overflow-wrap:anywhere" in admin
    assert "overflow-x:hidden" in dashboard or "overflow-wrap:anywhere" in dashboard
