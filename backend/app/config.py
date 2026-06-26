"""Application configuration"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = "postgresql:///arcade_management?host=/var/run/postgresql&port=5433"

    # Security
    secret_key: str = "ArcadeSecure2024!ChangeThisInProduction"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Application
    app_name: str = "Arcade Management System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Security
    bcrypt_rounds: int = 12
    mfa_issuer: str = "Arcade Management"
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    # Rate limiting
    rate_limit_per_minute: int = 100

    # Hosting
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()