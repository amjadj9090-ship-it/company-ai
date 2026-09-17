from pathlib import Path

ROOT = Path(__file__).parents[2]
BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend"


def read_backend(name: str) -> str:
    return (BACKEND / name).read_text(encoding="utf-8")


def read_frontend(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_core_route_modules_remain_present_and_registered():
    main = read_backend("main.py")
    orders = read_backend("orders.py")
    realtime = read_backend("realtime_routes.py")
    for module in ("orders", "realtime_routes"):
        assert module in main
    assert 'prefix="/api/orders"' in orders
    assert '@router.post("/api/voice-avatar/realtime-call")' in realtime


def test_orders_lifecycle_contract_remains_consistent():
    orders = read_backend("orders.py")
    assert 'Entity.kind == "orders"' in orders
    for status in ("confirmed", "in_progress", "completed", "cancelled"):
        assert status in orders
    for payment_status in ("unpaid", "pending", "paid", "refunded"):
        assert payment_status in orders


def test_realtime_contract_remains_provider_centralized():
    realtime = read_backend("realtime_routes.py")
    assert 'REALTIME_MODEL = "gpt-realtime-2.1"' in realtime
    assert "def _provider_headers(" in realtime
    assert "def _provider_error(" in realtime
    assert "LOGGER = logging.getLogger(" in realtime
    assert "print(" not in realtime


def test_admin_security_contract_remains_enforced():
    admin = read_backend("admin_compat.py")
    assert "def _admin_user(" in admin
    assert "Header(None)" in admin
    assert 'authorization.lower().startswith("bearer ")' in admin
    assert 'user.role not in {"admin", "owner"}' in admin
    assert "not user.active" in admin


def test_error_and_security_contract_remains_present():
    main = read_backend("main.py")
    assert "class SecurityMiddleware" in main
    assert "Request too large" in main
    assert "Rate limit exceeded" in main
    assert "X-Content-Type-Options" in main
    assert "X-Frame-Options" in main
    assert "Content-Security-Policy" in main


def test_public_pages_remain_mobile_rtl_ready():
    for name in ("index.html", "admin.html", "dashboard.html"):
        html = read_frontend(name)
        assert '<meta name="viewport" content="width=device-width,initial-scale=1">' in html
        assert 'lang="ar"' in html
        assert 'dir="rtl"' in html
        assert "overflow" in html


def test_layan_voice_frontend_contract_remains_wired():
    html = read_frontend("index.html")
    realtime = (FRONTEND / "layan-realtime-hotfix.js").read_text(encoding="utf-8")
    assert "startLayanVoice" in realtime
    assert "voiceChoice" in html
    assert "getUserMedia" in realtime
    assert "realtime-call" in realtime
    assert "layan-realtime-hotfix.js" in html


# Stage 17 regression suite trigger/marker.
