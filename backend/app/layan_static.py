from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

router = APIRouter()

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
_HOTFIX = _FRONTEND / "layan-realtime-hotfix.js"
_INTERACTIVE = _FRONTEND / "company-ai-interactive.js"

# Keep the public Layan asset URL alive even when the binary portrait asset is
# not present in the deployment bundle. This prevents a broken-image failure
# in the realtime overlay and gives the voice UI a deterministic visual base.
_LAYAN_FALLBACK_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 900 1200\"><defs><linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop stop-color=\"#17324f\"/><stop offset=\"1\" stop-color=\"#06101d\"/></linearGradient><linearGradient id=\"dress\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop stop-color=\"#eef5ff\"/><stop offset=\"1\" stop-color=\"#b9c8dc\"/></linearGradient></defs><rect width=\"900\" height=\"1200\" fill=\"url(#bg)\"/><circle cx=\"450\" cy=\"380\" r=\"145\" fill=\"#d9b39b\"/><path d=\"M300 385c15-190 285-220 300 0-45-60-78-92-150-98-72 6-105 38-150 98z\" fill=\"#34251f\"/><path d=\"M315 555c35-78 90-118 135-118s100 40 135 118l90 500H225z\" fill=\"url(#dress)\"/><circle cx=\"395\" cy=\"375\" r=\"10\" fill=\"#172235\"/><circle cx=\"505\" cy=\"375\" r=\"10\" fill=\"#172235\"/><path d=\"M410 445c28 18 52 18 80 0\" fill=\"none\" stroke=\"#8b5f55\" stroke-width=\"7\" stroke-linecap=\"round\"/><text x=\"450\" y=\"1110\" text-anchor=\"middle\" fill=\"#dcecff\" font-family=\"Arial,sans-serif\" font-size=\"34\" font-weight=\"700\">LAYAN · COMPANY AI</text></svg>"""


@router.get("/layan-realtime-hotfix.js", include_in_schema=False)
def layan_realtime_hotfix():
    # The homepage already loads this URL. Bundle the public interaction bridge
    # here as well so the existing production index becomes functional without
    # changing the large HTML asset or risking duplicate script tags.
    try:
        content = _HOTFIX.read_text(encoding="utf-8") + "\n" + _INTERACTIVE.read_text(encoding="utf-8")
        return Response(content=content, media_type="application/javascript")
    except Exception:
        return FileResponse(_HOTFIX, media_type="application/javascript")


@router.get("/assets/layan-office.webp", include_in_schema=False)
def layan_office_asset():
    return Response(content=_LAYAN_FALLBACK_SVG, media_type="image/svg+xml")
