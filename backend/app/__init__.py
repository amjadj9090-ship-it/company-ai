from fastapi import FastAPI


def _install_central_brain_router() -> None:
    from .central_brain import router

    original_init = FastAPI.__init__
    if getattr(FastAPI, "_company_ai_brain_installed", False):
        return

    def company_ai_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if getattr(self, "title", "") == "Company AI Global Business OS":
            self.include_router(router)

    FastAPI.__init__ = company_ai_init
    FastAPI._company_ai_brain_installed = True


_install_central_brain_router()
