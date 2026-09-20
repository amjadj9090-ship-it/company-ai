"""Independent Company AI launch backend package.

The Render entrypoint remains launch_backend:app. This package exposes the
application defined in the sibling launch_backend.py without importing or
depending on the legacy backend/frontend tree.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_runtime_path = Path(__file__).resolve().parent.parent / "launch_backend.py"
_spec = spec_from_file_location("company_ai_launch_runtime", _runtime_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Unable to load independent launch runtime")

_runtime = module_from_spec(_spec)
_spec.loader.exec_module(_runtime)
app = _runtime.app
