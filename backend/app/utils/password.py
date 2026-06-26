"""Password hashing and verification utilities"""
import bcrypt
from passlib.context import CryptContext

# Create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Ensure password is a string and truncate if too long (bcrypt limit)
    if not isinstance(password, str):
        password = str(password)

    # Truncate to 72 characters if longer
    if len(password) > 72:
        password = password[:72]

    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Get password hash (alias for hash_password).

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return hash_password(password)