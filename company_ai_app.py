"""Render entrypoint for the complete Company AI application.

The live service uses the production-tested backend app so the public site,
Layan, CRM, Central AI, security middleware and API routes stay on one stack.
"""
from backend.app.main import app
