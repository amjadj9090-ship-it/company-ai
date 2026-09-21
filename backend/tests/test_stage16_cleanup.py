from pathlib import Path

ROOT = Path(__file__).parents[2]
REALTIME = ROOT / "backend" / "app" / "realtime_routes.py"


def test_realtime_provider_helpers_are_centralized():
    source = REALTIME.read_text(encoding="utf-8")
    assert "OPENAI_CLIENT_SECRETS_URL" in source
    assert "def _provider_headers(" in source
    assert "def _provider_error(" in source
    assert "_provider_headers(api_key)" in source
    assert "_provider_headers(api_key, json_content=True)" in source


def test_realtime_routes_use_structured_logging():
    source = REALTIME.read_text(encoding="utf-8")
    assert "import logging" in source
    assert "LOGGER = logging.getLogger(" in source
    assert "print(" not in source
