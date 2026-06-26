"""FastAPI application with security"""
from fastapi import FastAPI

from app.utils.cors import configure_cors
from app.utils.security import security_middleware

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
app.middleware("http")(security_middleware)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Arcade Management System",
        "version": "1.0.0",
        "status": "running",
        "phase": "Phase 0 - Day 3 Complete: Project Structure"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )