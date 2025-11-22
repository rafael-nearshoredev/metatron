from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .config import settings
from .api import register_routes
from .middleware import CaseConverterMiddleware


app = FastAPI(
    swagger_parameters = {
        "tagsSorter": "alpha",  
        "operationsSorter": "alpha", 
        "tryItOutEnabled": True,  
        "defaultModelExpandDepth": 1,
        "docExpansion": "none",
        "deepLinking": True,
        "displayOperationId": True,
        "showExtensions": True,
        "persistAuthorization": True,
        "defaultModelsExpandDepth": -1,
    },
    title="Metatron Service API",
    description="A Metatron service with FastAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(CaseConverterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5080", "http://127.0.0.1:5080", "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (including 404 Not Found)"""
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": f"The requested endpoint '{request.url.path}' was not found",
                "status_code": 404
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors (400 Bad Request)"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "status_code": 400
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions (500 Internal Server Error)"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request",
            "status_code": 500
        }
    )
# Root redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation"""
    return RedirectResponse(url="/docs")

register_routes(app)


def main():
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
