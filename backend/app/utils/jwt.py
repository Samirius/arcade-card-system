"""JWT token creation and validation"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
SECRET_KEY = settings.secret_key

def create_access_token(data: Dict[str, Any], token_version: Optional[int] = None, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        token_version: User's token version for revocation checking
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    # Add token_version if provided
    if token_version is not None:
        to_encode["token_version"] = token_version

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Data to encode in the token

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify an access token and return the payload.

    Args:
        token: JWT access token

    Returns:
        Token payload or None if invalid
    """
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    return payload

def verify_refresh_token(token: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """
    Verify a refresh token and return the payload.

    Args:
        token: JWT refresh token
        db: Database session to check blacklist

    Returns:
        Token payload or None if invalid
    """
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get("type") != "refresh":
        return None

    # Check blacklist if database provided
    if db:
        from app.models.refresh_token import RefreshTokenBlacklist
        from hashlib import sha256

        # Check if token is blacklisted
        token_hash = sha256(token.encode()).hexdigest()
        blacklisted = db.query(RefreshTokenBlacklist).filter(
            RefreshTokenBlacklist.token_hash == token_hash
        ).first()

        if blacklisted:
            return None

    return payload

def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiry time of a token.

    Args:
        token: JWT token

    Returns:
        Expiry datetime or None if invalid
    """
    payload = decode_token(token)
    if not payload:
        return None

    exp = payload.get("exp")
    if not exp:
        return None

    return datetime.fromtimestamp(exp)