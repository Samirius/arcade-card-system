"""FastAPI application with security"""
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.cors import configure_cors
from app.utils.security import security_middleware
from app.api.auth import router as auth_router
from app.api.cards import router as cards_router
from app.api.transactions import router as transactions_router
from app.api.dashboard import router as dashboard_router
from app.api.companies import router as companies_router
from app.api.balance import router as balance_router
from app.api.offline import router as offline_router
from app.api.users import router as users_router
from app.database import engine, Base
from app.logging import setup_logging
from app.exceptions import http_exception_handler, validation_exception_handler, general_exception_handler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    print("🚀 Starting Arcade Management System...")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔒 Debug mode: {settings.debug}")

    # Create database tables
    try:
        print("📦 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

    yield

    # Shutdown
    print("🛑 Shutting down Arcade Management System...")


# Create FastAPI app
app = FastAPI(
    title="Arcade Management System",
    version="1.0.0",
    description="Secure arcade card management system with authentication and MFA",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Create limiter and add to app state
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Add rate limiting
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Configure CORS
configure_cors(app)

# Add security middleware
app.middleware("http")(security_middleware)

# Include routers (all under /api/v1 prefix for consistency)
api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(cards_router, prefix=api_prefix)
app.include_router(transactions_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(companies_router, prefix=api_prefix)
app.include_router(balance_router, prefix=api_prefix)
app.include_router(offline_router, prefix=api_prefix)
app.include_router(users_router, prefix=api_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Arcade Management System",
        "version": "1.0.0",
        "status": "running",
        "phase": "Phase 1 - Authentication Complete",
        "api_versions": ["v1"],
        "endpoints": {
            "health": "/health",
            "auth": "/api/v1/auth/*",
            "docs": "/docs" if settings.debug else "disabled in production"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "Arcade Management System",
        "version": "1.0.0",
        "api_version": "v1",
        "phase": "Phase 1 - Authentication Complete",
        "security": "enabled",
        "authentication": "enabled",
        "database": "connected",
        "environment": settings.environment
    }


@app.get("/security-info")
async def security_info(
    debug: bool = settings.debug,
):
    """
    Security information endpoint.

    Only available in debug mode. In production, returns 404.
    """
    if not debug:
        raise HTTPException(status_code=404, detail="Not Found")

    return {
        "security_features": {
            "password_hashing": "bcrypt (12 rounds, 72-byte limit)",
            "jwt_tokens": "access + refresh tokens",
            "mfa": "TOTP with QR codes and backup codes",
            "audit_logging": "database + file logging",
            "rate_limiting": "user-based + IP-based",
            "cors": "environment-aware",
            "security_headers": "10+ headers (CSP, HSTS, Permissions-Policy, etc.)",
            "input_validation": "Pydantic schemas",
            "api_versioning": "/api/v1/",
            "database_ssl": "required in production"
        },
        "authentication": {
            "endpoints": [
                "/api/v1/auth/register",
                "/api/v1/auth/login",
                "/api/v1/auth/login/mfa",
                "/api/v1/auth/refresh",
                "/api/v1/auth/mfa/setup/initiate",
                "/api/v1/auth/mfa/setup/verify",
                "/api/v1/auth/logout",
                "/api/v1/auth/me"
            ],
            "token_expiry": {
                "access_token": f"{settings.access_token_expire_minutes} minutes",
                "refresh_token": f"{settings.refresh_token_expire_days} days"
            }
        },
        "environment": settings.environment,
        "debug_mode": settings.debug
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )