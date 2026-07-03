"""Rate limiting utilities"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from typing import Optional
from collections import defaultdict
import time

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# In-memory rate limiter (for development - use Redis in production)
class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()

    def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Check if a request is rate limited.

        Args:
            key: Unique key for the requestor (e.g., IP, user ID)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if rate limited, False otherwise
        """
        # Clean up old entries periodically
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self.cleanup()

        now = time.time()
        window_start = now - window_seconds

        # Get recent requests for this key
        recent_requests = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]

        # Check if limit exceeded
        if len(recent_requests) >= max_requests:
            return True

        # Add current request
        self.requests[key].append(now)
        return False

    def cleanup(self):
        """Clean up old entries"""
        self.last_cleanup = time.time()
        now = time.time()
        one_hour_ago = now - 3600

        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > one_hour_ago
            ]

            # Remove empty entries
            if not self.requests[key]:
                del self.requests[key]

# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()

def get_client_ip(request: Request) -> str:
    """
    Get the client's IP address from the request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for forwarded IP (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Get direct IP
    return request.client.host if request.client else "unknown"

def check_rate_limit(
    request: Request,
    max_requests: int,
    window_seconds: int,
    user_id: Optional[str] = None
) -> bool:
    """
    Check if a request should be rate limited.

    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        user_id: Optional user ID for user-based limiting

    Returns:
        True if rate limited, False otherwise
    """
    # Use user_id if provided, otherwise use IP
    key = user_id if user_id else get_client_ip(request)

    return rate_limiter.is_rate_limited(
        key=key,
        max_requests=max_requests,
        window_seconds=window_seconds
    )