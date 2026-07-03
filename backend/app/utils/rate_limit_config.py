"""Rate limiting configuration and middleware"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)


def get_user_id(request: Request) -> str:
    """
    Get user ID for rate limiting.

    Falls back to IP address if user not authenticated.
    """
    # Try to get user from request state (set by authentication middleware)
    if hasattr(request.state, 'user') and request.state.user:
        return str(request.state.user.id)

    # Fall back to IP address
    return get_remote_address(request)


def is_rate_limit_exceeded(request: Request) -> bool:
    """
    Check if rate limit is exceeded for this request.
    """
    # This will be handled by the @limiter.limit decorator
    return False