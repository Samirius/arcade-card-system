"""CORS configuration utilities"""
from fastapi.middleware.cors import CORSMiddleware
from typing import List

def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins based on environment.

    Returns:
        List of allowed origins
    """
    # Development: allow local origins
    return [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]

def configure_cors(app) -> None:
    """
    Configure CORS middleware for the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
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