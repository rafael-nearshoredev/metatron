"""
Custom middleware for the FastAPI application.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CaseConverterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle case conversion if needed.
    Currently a pass-through middleware.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response