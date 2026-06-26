"""Authentication API routes"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import re

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.services.auth import AuthService
from app.config import settings

# Create router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Security
security = HTTPBearer(auto_error=False)


def validate_password_strength(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 12:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True


class UserCreateRequest(BaseModel):
    """User registration request with validation"""
    email: str
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: Optional[str] = "STAFF"

    @field_validator('email', mode='before')
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        return v.lower()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not validate_password_strength(v):
            raise ValueError('Password must be 12+ characters with uppercase, lowercase, numbers, and special characters')
        return v


class MFAVerifyRequest(BaseModel):
    """MFA verification request"""
    mfa_code: str

    @field_validator('mfa_code')
    @classmethod
    def mfa_code_length(cls, v: str) -> str:
        if len(v) != 6:
            raise ValueError('MFA code must be 6 digits')
        if not v.isdigit():
            raise ValueError('MFA code must be numeric')
        return v


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    from app.utils.jwt import decode_token
    payload = decode_token(credentials.credentials)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_id = payload.get("sub")
    user = AuthService.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not active"
        )

    # Check token_version if present in token
    token_version = payload.get("token_version")
    if token_version is not None:
        from app.models.user import User
        current_version = db.query(User.token_version).filter(
            User.id == user_id
        ).scalar()

        if current_version is None or token_version != current_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user_data: UserCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    - Email must be unique
    - Password must be 12-72 characters with complexity requirements
    - Default role: STAFF
    - Default status: PENDING (requires email verification)
    - Sends verification email
    """
    try:
        user = AuthService.register_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=user_data.role or UserRole.STAFF
        )

        # Send verification email
        from app.utils.email_verification import create_email_verification_token, send_verification_email
        token = create_email_verification_token(user.email)
        send_verification_email(user.email, token)

        return {
            "message": "User registered successfully. Please check your email for verification.",
            "user_id": str(user.id),
            "email": user.email,
            "status": user.status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login")
async def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login with email and password."""
    try:
        client_ip = request.client.host if request.client else "unknown"
        user, access_token, refresh_token = AuthService.authenticate_user(
            db=db,
            email=login_data.email,
            password=login_data.password,
            client_ip=client_ip
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "expires_at": str(datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)),
            "warning_threshold": 300,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "status": user.status,
                "mfa_enabled": user.mfa_enabled
            },
            "requires_mfa": user.mfa_enabled
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/login/mfa")
async def login_with_mfa(
    request: Request,
    login_data: UserLogin,
    mfa_request: MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """Login with email, password, and MFA code."""
    try:
        client_ip = request.client.host if request.client else "unknown"
        user, access_token, refresh_token = AuthService.authenticate_user(
            db=db,
            email=login_data.email,
            password=login_data.password,
            mfa_code=mfa_request.mfa_code,
            client_ip=client_ip
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "expires_at": str(datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)),
            "warning_threshold": 300,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "status": user.status,
                "mfa_enabled": user.mfa_enabled
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        user, access_token = AuthService.refresh_token(
            db=db,
            refresh_token_str=refresh_token
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "expires_at": str(datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)),
            "warning_threshold": 300,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "status": user.status,
                "mfa_enabled": user.mfa_enabled
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/mfa/setup/initiate")
async def initiate_mfa_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate MFA setup."""
    try:
        qr_code_url = AuthService.setup_mfa_initiation(db, str(current_user.id))
        return {
            "qr_code_url": qr_code_url,
            "message": "Scan QR code with authenticator app, then verify with /mfa/setup/verify"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/mfa/setup/verify")
async def verify_mfa_setup(
    mfa_request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify MFA setup and enable MFA for user."""
    try:
        qr_code_url, backup_codes = AuthService.enable_mfa(
            db=db,
            user_id=str(current_user.id),
            mfa_code=mfa_request.mfa_code
        )
        return {
            "message": "MFA enabled successfully",
            "qr_code_url": qr_code_url,
            "backup_codes": backup_codes,
            "warning": "Save backup codes securely. You'll need them if you lose access to your authenticator app."
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    logout_data: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user."""
    from app.models.refresh_token import RefreshTokenBlacklist
    from app.utils.jwt import create_access_token
    from hashlib import sha256

    # Get refresh token from request body or authorization header
    refresh_token = None
    if logout_data and "refresh_token" in logout_data:
        refresh_token = logout_data["refresh_token"]
    else:
        # Try to get from authorization header if Bearer token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # This would be the access token, not refresh token
            # We need the frontend to send refresh_token in body
            pass

    # Invalidate all tokens by incrementing token version
    from sqlalchemy import text
    db.execute(
        text("UPDATE users SET token_version = token_version + 1 WHERE id = :user_id"),
        {"user_id": str(current_user.id)}
    )
    db.commit()

    # Blacklist the refresh token if provided
    if refresh_token:
        token_hash = sha256(refresh_token.encode()).hexdigest()
        expiry = datetime.utcnow() + timedelta(days=7)  # Refresh token expiry

        blacklist_entry = RefreshTokenBlacklist(
            token_hash=token_hash,
            revoked_at=datetime.utcnow(),
            expires_at=expiry,
            user_id=str(current_user.id),
            revocation_reason="LOGOUT"
        )

        db.add(blacklist_entry)
        db.commit()

    return {"message": "Logged out successfully", "tokens_revoked": True}


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "status": current_user.status,
        "mfa_enabled": current_user.mfa_enabled
    }


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify user email address.

    Validates the JWT token and activates the user account.
    """
    from app.utils.email_verification import verify_email_token

    # Verify token
    email = verify_email_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Find user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already verified
    if user.is_verified:
        return {
            "message": "Email already verified",
            "email": user.email
        }

    # Mark as verified and active
    user.is_verified = True
    user.status = UserStatus.ACTIVE
    user.updated_at = datetime.utcnow()
    db.commit()

    # Log verification
    from app.utils.audit import log_audit
    log_audit(
        db=db,
        user_id=user.id,
        action="UPDATE",
        resource_type="user",
        resource_id=user.id,
        old_values={"is_verified": False, "status": "PENDING"},
        new_values={"is_verified": True, "status": "ACTIVE"}
    )

    return {
        "message": "Email verified successfully",
        "email": user.email,
        "status": "ACTIVE"
    }