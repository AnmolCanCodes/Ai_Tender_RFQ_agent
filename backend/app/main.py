"""
AI Tender & RFQ Intelligence Platform - Main FastAPI Application.
Wires dependency injection, zero-trust security middleware, and REST API routing.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.company import router as company_router
from app.api.documents import router as documents_router
from app.api.intelligence import router as intelligence_router
from app.api.requirements import router as requirements_router
from app.api.tenders import router as tenders_router
from app.core.config import settings

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

app = FastAPI(
    title="AI Tender & RFQ Intelligence Platform",
    description="Enterprise procurement analysis, evidence-backed RAG, and Bid/No-Bid readiness evaluation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cross-Origin Resource Sharing (CORS)
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if settings.ENVIRONMENT != "development" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Data Leakage Prevention: Masks internal server errors and stack traces from external clients.
    Logs full trace internally for security auditing.
    """
    logger.error("Unhandled server exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )


# Health and root status checks
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container orchestrators and load balancers."""
    return {
        "status": "healthy",
        "service": "ai-tender-platform",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Health"])
def root():
    """Service landing endpoint."""
    return {
        "message": "Welcome to AI Tender & RFQ Intelligence Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# Mount API routers under /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenders_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(requirements_router, prefix="/api/v1")
app.include_router(company_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")

# Also alias /auth for OAuth2 password flow compatibility
app.include_router(auth_router)
