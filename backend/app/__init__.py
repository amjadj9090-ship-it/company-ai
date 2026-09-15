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

# Feature routers are installed while the app is constructed, before main.py
# declares generic /api/{kind}/{entity_id} routes.
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

    # FastAPI's decorators ultimately register through the router. Intercept
    # the two generic entity routes so a literal entity id must be numeric;
    # otherwise a request such as POST /api/commercial/quotes can be consumed
    # by GET /api/{kind}/{entity_id} and incorrectly return 405.
    original_add_api_route = self.router.add_api_route

    def add_api_route_ordered(path, *route_args, **route_kwargs):
        if path in {'/api/{kind}/{entity_id}', '/api/{kind}/{entity_id}/'}:
            path = '/api/{kind}/{entity_id:int}'
        return original_add_api_route(path, *route_args, **route_kwargs)

    self.router.add_api_route = add_api_route_ordered


FastAPI.__init__ = _company_ai_init
