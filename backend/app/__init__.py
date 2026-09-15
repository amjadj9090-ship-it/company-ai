from fastapi import FastAPI


def _install_company_ai_routers() -> None:
    from .central_brain import router as brain_router
    from .ai_employees import router as employee_router
    from .crm import router as crm_router

    original_init = FastAPI.__init__
    if getattr(FastAPI, "_company_ai_routers_installed", False):
        return

    def company_ai_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if getattr(self, "title", "") == "Company AI Global Business OS":
            self.include_router(brain_router)
            self.include_router(employee_router)
            self.include_router(crm_router)

    FastAPI.__init__ = company_ai_init
    FastAPI._company_ai_routers_installed = True


_install_company_ai_routers()
