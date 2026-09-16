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
    for module in ("orders", "realtime_routes"):
        assert module in main
    assert "/api/orders" in main
    assert "/api/voice-avatar" in main


def test_orders_lifecycle_contract_remains_consistent():
    orders = read_backend("orders.py")
    lifecycle = read_backend("lifecycle.py")
    assert 'Entity.kind == "orders"' in orders
    assert 'kind="orders"' in lifecycle
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
    assert "Authorization" in admin
    assert "Bearer " in admin
    assert "role in {\"admin\", \"owner\"}" in admin
    assert "is_active" in admin


def test_error_contract_and_request_ids_remain_present():
    errors = read_backend("errors.py")
    main = read_backend("main.py")
    assert "request_id" in errors
    assert "request_id" in main


def test_public_pages_remain_mobile_rtl_ready():
    for name in ("index.html", "admin.html", "dashboard.html"):
        html = read_frontend(name)
        assert '<meta name="viewport" content="width=device-width,initial-scale=1">' in html
        assert 'lang="ar"' in html
        assert 'dir="rtl"' in html
        assert "overflow" in html


def test_layan_voice_frontend_contract_remains_wired():
    html = read_frontend("index.html")
    realtime = (FRONTEND / "layan-realtime-ga-fix.js").read_text(encoding="utf-8")
    assert "startLayanVoice" in realtime
    assert "voiceChoice" in realtime
    assert "getUserMedia" in realtime
    assert "realtime-call" in realtime
    assert "layan-realtime-ga-fix.js" in html


# Stage 17 regression suite trigger/marker.
