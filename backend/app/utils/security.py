"""Security middleware for FastAPI"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Callable
from functools import wraps
import time

security = HTTPBearer(auto_error=False)

async def security_middleware(request: Request, call_next):
    """
    Security middleware for request processing.

    Args:
        request: FastAPI request object
        call_next: Next middleware in chain

    Returns:
        Response from next middleware
    """
    from app.utils.rate_limit import check_rate_limit, get_client_ip

    # Rate limiting check
    ip_address = get_client_ip(request)
    if check_rate_limit(
        request=request,
        max_requests=100,
        window_seconds=60,
        user_id=ip_address
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )

    # Process request
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; object-src 'none'"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

    return response

async def require_auth(request: Request) -> Optional[dict]:
    """
    Require authentication for an endpoint.

    Args:
        request: FastAPI request object

    Returns:
        User ID from JWT token

    Raises:
        HTTPException: If not authenticated
    """
    credentials: HTTPAuthorizationCredentials = await security(request)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    from app.utils.jwt import verify_access_token
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return user_id

async def require_role(required_role: str, request: Request) -> Optional[dict]:
    """
    Require a specific user role for an endpoint.

    Args:
        required_role: Required role level
        request: FastAPI request object

    Returns:
        User ID from JWT token

    Raises:
        HTTPException: If role doesn't match
    """
    user_id = await require_auth(request)

    # Get user from database (would need actual implementation)
    # For now, just return user_id
    return user_id

def require_mfa(func: Callable) -> Callable:
    """
    Decorator to require MFA for an endpoint.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if user has MFA enabled
        # Would need to fetch user from database
        # For now, just proceed
        return await func(*args, **kwargs)
    return wrapper

def log_request(func: Callable) -> Callable:
    """
    Decorator to log all requests.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            # Log successful request
            print(f"✅ {func.__name__} completed in {duration:.2f}s")

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Log failed request
            print(f"❌ {func.__name__} failed in {duration:.2f}s: {e}")

            raise

    return wrapper