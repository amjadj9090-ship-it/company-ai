from pathlib import Path


FRONTEND = Path(__file__).parents[2] / "frontend"


def read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_public_and_admin_pages_are_arabic_rtl_and_mobile_ready():
    for name in ("index.html", "admin.html", "dashboard.html"):
        html = read(name)
        assert '<meta name="viewport" content="width=device-width,initial-scale=1">' in html
        assert 'lang="ar"' in html
        assert 'dir="rtl"' in html


def test_mobile_layout_contracts_exist():
    index = read("index.html")
    admin = read("admin.html")
    dashboard = read("dashboard.html")

    assert "@media(max-width:520px)" in index
    assert 'id="layanVoiceEntry"' in index
    assert 'onclick="openLayanVoice();return false;"' in index
    assert '/assets/layan-office.webp' in index
    assert "@media(max-width:700px)" in admin
    assert "@media(max-width:500px)" in dashboard
    assert "min-height:44px" in admin
    assert "mobileNav" in dashboard


def test_arabic_mobile_pages_have_overflow_protection_or_responsive_contracts():
    index = read("index.html")
    admin = read("admin.html")
    dashboard = read("dashboard.html")

    assert "overflow-x:hidden" in admin or "overflow-wrap:anywhere" in admin
    assert "overflow-x:hidden" in dashboard or "overflow-wrap:anywhere" in dashboard
    assert "@media(max-width:520px)" in index
