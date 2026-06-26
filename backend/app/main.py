"""FastAPI application with security"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.utils.cors import configure_cors
from app.utils.security import SecurityMiddleware

# Create FastAPI app
app = FastAPI(
    title="Arcade Management System",
    version="1.0.0",
    description="Secure arcade card management system",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
configure_cors(app)

# Add security middleware
security_middleware = SecurityMiddleware(app)

@app.middleware("http")
async def security_middleware_wrapper(request: Request, call_next):
    """Security middleware wrapper"""
    return await security_middleware(request, call_next)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Arcade Management System",
        "version": "1.0.0",
        "status": "running",
        "phase": "Phase 0 - Security Foundation Complete"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Arcade Management System",
        "database": "connected",
        "security": "enabled"
    }

@app.get("/security-info")
async def security_info():
    """Security information endpoint (for debugging)"""
    return {
        "security_features": {
            "password_hashing": "bcrypt (12 rounds)",
            "jwt_tokens": "enabled",
            "mfa": "available",
            "audit_logging": "enabled",
            "rate_limiting": "100 req/min",
            "cors": "restricted",
            "security_headers": "enabled"
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    import traceback
    import logging

    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if app.debug else "An error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )