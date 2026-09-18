import logging
import uuid

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_LOG = logging.getLogger('company_ai')
_ORIGINAL_FASTAPI_INIT = FastAPI.__init__


def _route_score(route):
    """Prefer concrete/specific paths over generic parameterized paths."""
    path = getattr(route, 'path', '') or ''
    parts = [part for part in path.split('/') if part]
    static_parts = sum('{' not in part for part in parts)
    parameter_parts = sum('{' in part for part in parts)
    converter_parts = sum(':' in part for part in parts)
    return (static_parts, converter_parts, -parameter_parts, len(parts), len(path))


def _resort_routes(router):
    # Starlette returns 405 immediately when the first path match is only a
    # method-partial match. Keeping concrete feature routes ahead of generic
    # /api/{kind} and /api/{kind}/{entity_id} routes prevents that shadowing.
    router.routes.sort(key=_route_score, reverse=True)


def _error_response(request: Request, status_code: int, error_code: str, detail, request_id: str):
    return JSONResponse(
        status_code=status_code,
        content={'detail': detail, 'error_code': error_code, 'request_id': request_id},
        headers={'X-Request-ID': request_id},
    )


def _company_ai_init(self, *args, **kwargs):
    _ORIGINAL_FASTAPI_INIT(self, *args, **kwargs)

    from .admin_compat import router as admin_compat_router
    from .central_brain import router as brain_router
    from .ai_employees import router as employee_router
    from .crm import router as crm_router
    from .crm_sales_bridge import router as crm_sales_router
    from .commercial_finance import router as commercial_finance_router
    from .dashboard_static import router as dashboard_static_router
    from .orders import router as orders_router
    from .payments import router as payments_router
    from .public_lifecycle import router as public_lifecycle_router
    from .layan_static import router as layan_static_router
    from .ui_api import router as ui_api_router
    from .live_ui import router as live_ui_router

    self.include_router(live_ui_router)
    self.include_router(admin_compat_router)
    self.include_router(brain_router)
    self.include_router(employee_router)
    self.include_router(crm_router)
    self.include_router(crm_sales_router)
    self.include_router(commercial_finance_router)
    self.include_router(dashboard_static_router)
    self.include_router(orders_router)
    self.include_router(payments_router)
    self.include_router(public_lifecycle_router)
    self.include_router(layan_static_router)
    self.include_router(ui_api_router)
    _resort_routes(self.router)

    async def _request_id_middleware(request: Request, call_next):
        request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            _LOG.exception('Unhandled application error request_id=%s path=%s', request_id, request.url.path)
            raise
        response.headers['X-Request-ID'] = request_id
        return response

    self.middleware('http')(_request_id_middleware)

    async def _http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, 'request_id', uuid.uuid4().hex)
        return _error_response(request, exc.status_code, 'HTTP_ERROR', exc.detail, request_id)

    async def _validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, 'request_id', uuid.uuid4().hex)
        return _error_response(request, 422, 'VALIDATION_ERROR', exc.errors(), request_id)

    async def _unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, 'request_id', uuid.uuid4().hex)
        _LOG.exception('Unhandled application error request_id=%s path=%s', request_id, request.url.path, exc_info=exc)
        return _error_response(request, 500, 'INTERNAL_SERVER_ERROR', 'Internal server error', request_id)

    self.add_exception_handler(HTTPException, _http_exception_handler)
    self.add_exception_handler(RequestValidationError, _validation_exception_handler)
    self.add_exception_handler(Exception, _unhandled_exception_handler)

    # FastAPI decorators ultimately register through the router. Intercept the
    # generic entity-id route so literal feature routes cannot be shadowed by
    # /api/{kind}/{entity_id}; then re-sort after every later route addition.
    original_add_api_route = self.router.add_api_route

    def add_api_route_ordered(path, *route_args, **route_kwargs):
        if path in {'/api/{kind}/{entity_id}', '/api/{kind}/{entity_id}/'}:
            path = '/api/{kind}/{entity_id:int}'
        result = original_add_api_route(path, *route_args, **route_kwargs)
        _resort_routes(self.router)
        return result

    self.router.add_api_route = add_api_route_ordered


FastAPI.__init__ = _company_ai_init
