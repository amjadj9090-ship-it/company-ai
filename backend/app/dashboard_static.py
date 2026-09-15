from __future__ import annotations

import os
from fastapi import APIRouter
from starlette.responses import FileResponse

router = APIRouter()
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
DASHBOARD_FILE = os.path.join(FRONTEND_DIR, "dashboard.html")


@router.get("/dashboard.html", include_in_schema=False)
def dashboard_html():
    return FileResponse(DASHBOARD_FILE, media_type="text/html")


@router.get("/dashboard", include_in_schema=False)
def dashboard_short():
    return FileResponse(DASHBOARD_FILE, media_type="text/html")
