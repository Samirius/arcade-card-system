"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str

    # Security
    secret_key: str
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

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()