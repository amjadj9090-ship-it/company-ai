from fastapi import FastAPI

# Register Company AI feature routers at FastAPI app construction time, before
# main.py adds generic /api/{kind}/{entity_id} routes. This ordering matters:
# Starlette returns 405 on the first partial path match, so feature POST routes
# must be registered before the generic path routes.
_ORIGINAL_FASTAPI_INIT = FastAPI.__init__


def _company_ai_init(self, *args, **kwargs):
    _ORIGINAL_FASTAPI_INIT(self, *args, **kwargs)
    from .central_brain import router as brain_router
    from .ai_employees import router as employee_router
    from .crm import router as crm_router
    from .crm_sales_bridge import router as crm_sales_router
    from .commercial_finance import router as commercial_finance_router
    from .dashboard_static import router as dashboard_static_router
    from .payments import router as payments_router
    from .public_lifecycle import router as public_lifecycle_router

    self.include_router(brain_router)
    self.include_router(employee_router)
    self.include_router(crm_router)
    self.include_router(crm_sales_router)
    self.include_router(commercial_finance_router)
    self.include_router(dashboard_static_router)
    self.include_router(payments_router)
    self.include_router(public_lifecycle_router)


FastAPI.__init__ = _company_ai_init
