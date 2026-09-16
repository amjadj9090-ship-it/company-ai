from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse, Response

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'frontend'
BRIDGE_VERSION = '20260916-04'

@router.get('/', include_in_schema=False)
def live_home():
    html = (FRONTEND / 'index.html').read_text(encoding='utf-8')
    html = html.replace('layan-realtime-hotfix.js?v=20260915-01', f'layan-realtime-hotfix.js?v={BRIDGE_VERSION}')
    marker = f'<script src="company-ai-live-bridge.js?v={BRIDGE_VERSION}"></script>'
    if marker not in html:
        html = html.replace('</body>', marker + '</body>')
    return HTMLResponse(
        html,
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Company-AI-UI': BRIDGE_VERSION,
        },
    )

@router.get('/company-ai-live-bridge.js', include_in_schema=False)
def live_bridge():
    return FileResponse(
        FRONTEND / 'company-ai-live-bridge.js',
        media_type='application/javascript',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'X-Company-AI-UI': BRIDGE_VERSION,
        },
    )

@router.get('/ui-version', include_in_schema=False)
def ui_version():
    return Response(
        content=BRIDGE_VERSION,
        media_type='text/plain',
        headers={'Cache-Control': 'no-store', 'X-Company-AI-UI': BRIDGE_VERSION},
    )
