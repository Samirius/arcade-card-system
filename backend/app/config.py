"""Application configuration"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///arcade_management?host=/var/run/postgresql&port=5433")

# Security - from environment with validation
SECRET_KEY = os.getenv("SECRET_KEY", "")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be at least 32 characters")

# Application
APP_NAME = "Arcade Management System"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Security
BCRYPT_ROUNDS = 12
MFA_ISSUER = "Arcade Management"
MAX_LOGIN_ATMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# Rate limiting
RATE_LIMIT_PER_MINUTE = 100

# Hosting
HOST = "0.0.0.0"
PORT = 8000

class Settings:
    """Application settings"""
    
    # Database
    database_url: str = DATABASE_URL
    
    # Security
    secret_key: str = SECRET_KEY
    
    # Application
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    debug: bool = DEBUG
    environment: str = ENVIRONMENT
    
    # Security settings
    bcrypt_rounds: int = BCRYPT_ROUNDS
    mfa_issuer: str = MFA_ISSUER
    max_login_attempts: int = MAX_LOGIN_ATMPTS
    lockout_duration_minutes: int = LOCKOUT_DURATION_MINUTES
    
    # Rate limiting
    rate_limit_per_minute: int = RATE_LIMIT_PER_MINUTE
    
    # JWT settings
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Hosting
    host: str = HOST
    port: int = PORT
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list"""
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
        return [origin.strip() for origin in cors_origins.split(",")]

settings = Settings()

def get_cors_origins() -> List[str]:
    """Get CORS origins as list"""
    return settings.get_cors_origins()