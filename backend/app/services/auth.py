"""Authentication service for user management"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.user import User, UserRole, UserStatus
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token, create_refresh_token
from app.utils.mfa import generate_mfa_secret, verify_mfa_token, generate_mfa_qr_code
from app.utils.audit import log_audit
from app.config import settings


class AuthService:
    """Service for authentication operations"""

    @staticmethod
    def register_user(
        db: Session,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        role: UserRole = UserRole.STAFF
    ) -> User:
        """
        Register a new user.

        Args:
            db: Database session
            email: User email
            password: Plain text password
            first_name: User first name
            last_name: User last name
            phone: User phone (optional)
            role: User role (default: STAFF)

        Returns:
            Created user object

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("Email already registered")

        # Hash password
        password_hash = hash_password(password)

        # Create user
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            status=UserStatus.PENDING,
            is_verified=False
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Log registration
        log_audit(
            db=db,
            action="CREATE",
            resource_type="user",
            resource_id=user.id,
            new_values={
                "email": user.email,
                "role": user.role,
                "status": user.status
            }
        )

        return user

    @staticmethod
    def authenticate_user(
        db: Session,
        email: str,
        password: str,
        mfa_code: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """
        Authenticate user with email and password.

        Args:
            db: Database session
            email: User email
            password: Plain text password
            mfa_code: MFA code (if MFA enabled)

        Returns:
            Tuple of (user, access_token, refresh_token)

        Raises:
            ValueError: If credentials invalid, account locked, etc.
        """
        # Find user
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            raise ValueError("Invalid email or password")

        # Check if account is locked
        if user.is_locked():
            raise ValueError("Account is locked. Please contact administrator.")

        # Check account status
        if user.status != UserStatus.ACTIVE:
            raise ValueError("Account is not active. Please contact administrator.")

        # Verify password
        if not verify_password(password, user.password_hash):
            user.increment_failed_login()
            db.commit()
            raise ValueError("Invalid email or password")

        # Check if MFA is required
        if user.mfa_enabled:
            if not mfa_code:
                raise ValueError("MFA code required")
            if not verify_mfa_token(user.mfa_secret, mfa_code):
                user.increment_failed_login()
                db.commit()
                raise ValueError("Invalid MFA code")

        # Reset failed login attempts on successful authentication
        user.reset_failed_login()
        user.last_login = datetime.utcnow()
        db.commit()

        # Generate JWT tokens
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })
        refresh_token = create_refresh_token({
            "sub": str(user.id)
        })

        # Log successful login
        log_audit(
            db=db,
            user_id=user.id,
            action="LOGIN",
            resource_type="user",
            resource_id=user.id,
            ip_address=None,  # Will be set from request
            success=True
        )

        return user, access_token, refresh_token

    @staticmethod
    def enable_mfa(
        db: Session,
        user_id: str,
        mfa_code: str
    ) -> Tuple[str, str]:
        """
        Enable MFA for user after verifying code.

        Args:
            db: Database session
            user_id: User ID
            mfa_code: MFA code to verify

        Returns:
            Tuple of (qr_code_url, backup_codes)

        Raises:
            ValueError: If code invalid
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Verify the MFA code
        if not user.mfa_secret or not verify_mfa_token(user.mfa_secret, mfa_code):
            raise ValueError("Invalid MFA code")

        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]

        # Enable MFA
        user.mfa_enabled = True
        user.backup_codes = backup_codes
        user.updated_at = datetime.utcnow()
        db.commit()

        # Generate QR code URL
        qr_code_url = generate_qr_code(
            secret=user.mfa_secret,
            email=user.email,
            issuer=settings.mfa_issuer
        )

        # Log MFA enablement
        log_audit(
            db=db,
            user_id=user.id,
            action="CONFIG_CHANGE",
            resource_type="user",
            resource_id=user.id,
            new_values={"mfa_enabled": True}
        )

        return qr_code_url, backup_codes

    @staticmethod
    def setup_mfa_initiation(db: Session, user_id: str) -> str:
        """
        Initiate MFA setup by generating secret.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            QR code URL
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Generate MFA secret
        mfa_secret = generate_mfa_secret()

        # Store secret temporarily (not enabled yet)
        user.mfa_secret = mfa_secret
        user.updated_at = datetime.utcnow()
        db.commit()

        # Generate QR code URL
        qr_code_url = generate_qr_code(
            secret=mfa_secret,
            email=user.email,
            issuer=settings.mfa_issuer
        )

        return qr_code_url

    @staticmethod
    def refresh_token(db: Session, refresh_token_str: str) -> Tuple[User, str]:
        """
        Refresh access token using refresh token.

        Args:
            db: Database session
            refresh_token_str: Refresh token

        Returns:
            Tuple of (user, new_access_token)

        Raises:
            ValueError: If refresh token invalid
        """
        from app.utils.jwt import decode_token

        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()

        if not user or user.status != UserStatus.ACTIVE:
            raise ValueError("User not found or inactive")

        # Generate new access token
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })

        return user, access_token

    @staticmethod
    def logout_user(db: Session, user_id: str) -> None:
        """
        Logout user (token invalidation would be handled by client).

        Args:
            db: Database session
            user_id: User ID
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            log_audit(
                db=db,
                user_id=user_id,
                action="LOGOUT",
                resource_type="user",
                resource_id=user_id,
                success=True
            )

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email.lower()).first()

    @staticmethod
    def update_user_status(
        db: Session,
        user_id: str,
        status: UserStatus
    ) -> User:
        """Update user status"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        old_status = user.status
        user.status = status
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        log_audit(
            db=db,
            user_id=user_id,
            action="UPDATE",
            resource_type="user",
            resource_id=user_id,
            old_values={"status": old_status},
            new_values={"status": status}
        )

        return user