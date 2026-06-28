"""CORS configuration utilities"""
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.config import settings


def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins from environment configuration.

    Falls back to localhost origins only in debug mode.
    In production, CORS_ORIGINS env var must be set.
    """
    return settings.get_cors_origins()


def configure_cors(app) -> None:
    """
    Configure CORS middleware for the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    origins = get_cors_origins()

    if settings.debug:
        # In debug mode, also allow common dev origins
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]
        for origin in dev_origins:
            if origin not in origins:
                origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS"
        ],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin"
        ],
        expose_headers=[
            "Content-Length",
            "Content-Type"
        ],
        max_age=600,  # 10 minutes
    )
