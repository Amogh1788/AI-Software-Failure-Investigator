import logging
import traceback
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.repositories import router as repositories_router
from app.api.investigations import router as investigations_router

# Configure root logger
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("ai_investigator.app")

# Initialize FastAPI application with environment-controlled documentation
app = FastAPI(
    title="AI Software Failure Investigator API",
    description="Production API service for AI Software Failure Investigator — Phase 5 Production MVP",
    version="1.0.0",
    docs_url="/docs" if settings.is_docs_enabled else None,
    redoc_url="/redoc" if settings.is_docs_enabled else None,
)

# 1. Security Headers Middleware (outermost response headers)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# 4. Request Logging & Correlation ID Middleware (assigns request_id at request onset)
app.add_middleware(RequestLoggingMiddleware)


# ==============================================================================
# Centralized Error Handlers (Sanitized Output & Correlation ID)
# ==============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "req_unknown")
    headers = getattr(exc, "headers", None) or {}
    headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "detail": exc.detail,
            "request_id": request_id,
            "error_code": "HTTP_EXCEPTION",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "req_unknown")
    tb = traceback.format_exc()

    # Log full stack trace server-side with request ID
    logger.critical(f"[{request_id}] Unhandled Server Exception on {request.method} {request.url.path}:\n{tb}")

    # Return sanitized RFC-compliant error payload with zero path or code leakage
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": request_id},
        content={
            "detail": "An unexpected internal server error occurred.",
            "request_id": request_id,
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


# Mount API routers under /api
app.include_router(health_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(repositories_router, prefix="/api")
app.include_router(investigations_router, prefix="/api")


@app.get("/", tags=["Root"])
def root():
    """Root endpoint providing service metadata."""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.is_docs_enabled else "disabled",
        "endpoints": {
            "health": "/api/health",
            "health_live": "/api/health/live",
            "health_ready": "/api/health/ready",
            "database_health": "/api/health/db",
            "projects": "/api/projects",
            "repositories": "/api/repositories",
            "repositories_analyze": "/api/repositories/analyze",
            "investigations": "/api/investigations",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
