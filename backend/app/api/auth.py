"""Authentication API routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.services.auth import AuthService
from app.config import settings

# Create router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Security
security = HTTPBearer(auto_error=False)


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

    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    - Email must be unique
    - Password must be 8-72 characters
    - Default role: STAFF
    - Default status: PENDING (requires activation)
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
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login")
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns:
        - access_token: JWT token for API access (30 min expiry)
        - refresh_token: JWT token for refreshing access (7 days expiry)
        - user: User information
        - requires_mfa: Boolean indicating if MFA is required

    If MFA is enabled, returns `requires_mfa: true` and no tokens.
    Client should then call `/mfa/verify` with the MFA code.
    """
    try:
        user, access_token, refresh_token = AuthService.authenticate_user(
            db=db,
            email=login_data.email,
            password=login_data.password
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
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
    login_data: UserLogin,
    mfa_code: str,
    db: Session = Depends(get_db)
):
    """
    Login with email, password, and MFA code.

    Required if user has MFA enabled.
    """
    try:
        user, access_token, refresh_token = AuthService.authenticate_user(
            db=db,
            email=login_data.email,
            password=login_data.password,
            mfa_code=mfa_code
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
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
    """
    Refresh access token using refresh token.

    Returns:
        - access_token: New JWT token
        - user: User information
    """
    try:
        user, access_token = AuthService.refresh_token(
            db=db,
            refresh_token_str=refresh_token
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
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
    """
    Initiate MFA setup.

    Returns QR code URL for authenticator app.

    Requires authentication.
    """
    try:
        qr_code_url = AuthService.setup_mfa_initiation(db, str(current_user.id))

        return {
            "qr_code_url": qr_code_url,
            "secret": current_user.mfa_secret,
            "message": "Scan QR code with authenticator app, then verify with /mfa/setup/verify"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/mfa/setup/verify")
async def verify_mfa_setup(
    mfa_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify MFA setup and enable MFA for user.

    Call after scanning QR code from /mfa/setup/initiate.

    Returns backup codes for recovery.

    Requires authentication.
    """
    try:
        qr_code_url, backup_codes = AuthService.enable_mfa(
            db=db,
            user_id=str(current_user.id),
            mfa_code=mfa_code
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user.

    Client should discard tokens.

    Requires authentication.
    """
    AuthService.logout_user(db, str(current_user.id))
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.

    Requires authentication.
    """
    return current_user


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify user email address.

    In production, this would use a JWT token sent via email.
    For now, we'll implement a simplified version.
    """
    # TODO: Implement email verification with JWT tokens
    return {"message": "Email verification not yet implemented"}