"""
API module initialization.
"""

from fastapi import FastAPI
from .main import router


def register_routes(app: FastAPI) -> None:
    """Register all API routes to the FastAPI app."""
    app.include_router(router)