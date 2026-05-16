"""Compatibility module.

Routes have been moved to modular router scaffolds and legacy router module.
Import `router` from here remains backward-compatible for app startup.
"""
from app.api.router import api_router as router
