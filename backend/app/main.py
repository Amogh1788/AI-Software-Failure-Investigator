from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.repositories import router as repositories_router
from app.api.investigations import router as investigations_router

app = FastAPI(
    title="AI Software Failure Investigator API",
    description="Backend API service for AI Software Failure Investigator - Phase 3 Failure Evidence Collection",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "version": "0.3.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
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
        reload=True,
    )
