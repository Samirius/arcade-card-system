"""Password hashing and verification utilities"""
import bcrypt

# Bcrypt configuration
BCRYPT_ROUNDS = 12

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Ensure password is a string
    if not isinstance(password, str):
        password = str(password)

    # Truncate to 72 BYTES if longer (bcrypt byte limit, not character limit)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    # Ensure inputs are strings
    if not isinstance(plain_password, str):
        plain_password = str(plain_password)
    
    # Truncate to 72 BYTES to match hashing behavior
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Verify
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    """
    Get password hash (alias for hash_password).

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return hash_password(password)