from pathlib import Path

# Temporary runtime guard: repair a malformed Base declaration introduced in
# the previous admin-password hotfix before Python imports backend.app.main.
_MAIN_FILE = Path(__file__).with_name('main.py')
try:
    _source = _MAIN_FILE.read_text(encoding='utf-8')
    _broken = 'class Base(DeclarativeBase: pass'
    if _broken in _source:
        _MAIN_FILE.write_text(_source.replace(_broken, 'class Base(DeclarativeBase): pass', 1), encoding='utf-8')
except Exception:
    pass

from fastapi import FastAPI

_ORIGINAL_FASTAPI_INIT = FastAPI.__init__


def _company_ai_init(self, *args, **kwargs):
    _ORIGINAL_FASTAPI_INIT(self, *args, **kwargs)

    from .admin_compat import router as admin_compat_router
    from .central_brain import router as brain_router
    from .ai_employees import router as employee_router
    from .crm import router as crm_router
    from .crm_sales_bridge import router as crm_sales_router
    from .commercial_finance import router as commercial_finance_router
    from .dashboard_static import router as dashboard_static_router
    from .payments import router as payments_router
    from .public_lifecycle import router as public_lifecycle_router
    from .layan_static import router as layan_static_router
    from .ui_api import router as ui_api_router

    # Specific feature routes are installed before main.py generic entity routes.
    self.include_router(admin_compat_router)
    self.include_router(brain_router)
    self.include_router(employee_router)
    self.include_router(crm_router)
    self.include_router(crm_sales_router)
    self.include_router(commercial_finance_router)
    self.include_router(dashboard_static_router)
    self.include_router(payments_router)
    self.include_router(public_lifecycle_router)
    self.include_router(layan_static_router)
    self.include_router(ui_api_router)

    # Force generic entity ids to be numeric so literal feature routes cannot
    # be shadowed by /api/{kind}/{entity_id}.
    original_add_api_route = self.router.add_api_route

    def add_api_route_ordered(path, *route_args, **route_kwargs):
        if path in {'/api/{kind}/{entity_id}', '/api/{kind}/{entity_id}/'}:
            path = '/api/{kind}/{entity_id:int}'
        return original_add_api_route(path, *route_args, **route_kwargs)

    self.router.add_api_route = add_api_route_ordered


FastAPI.__init__ = _company_ai_init
