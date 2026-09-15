from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

_HOTFIX = Path(__file__).resolve().parents[2] / "frontend" / "layan-realtime-hotfix.js"


@router.get("/layan-realtime-hotfix.js", include_in_schema=False)
def layan_realtime_hotfix():
    return FileResponse(_HOTFIX, media_type="application/javascript")
