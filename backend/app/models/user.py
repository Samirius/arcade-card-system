"""User model for authentication and authorization"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """User roles with hierarchical permissions"""
    STAFF = "STAFF"                  # Basic operations (add cards, process transactions)
    SUPERVISOR = "SUPERVISOR"         # Staff + approve refunds, view reports
    REGIONAL_MGR = "REGIONAL_MGR"     # Supervisor + manage staff, view all locations
    ADMIN = "ADMIN"                   # Regional Manager + system configuration
    OWNER = "OWNER"                   # Admin + full access, billing


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "ACTIVE"                 # Normal operation
    INACTIVE = "INACTIVE"             # Account disabled
    LOCKED = "LOCKED"                 # Locked due to failed login attempts
    PENDING = "PENDING"               # Awaiting email verification


class User(Base):
    """
    User model for authentication and authorization.

    Hierarchical Roles:
    - STAFF: Basic operations
    - SUPERVISOR: Staff + refunds + reports
    - REGIONAL_MGR: Supervisor + staff management
    - ADMIN: Regional Manager + system config
    - OWNER: Admin + billing + full access
    """
    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)

    # Role and permissions
    role = Column(
        SQLEnum(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.STAFF,
        index=True
    )

    # Account status
    status = Column(
        SQLEnum(UserStatus, name="user_status", create_type=True),
        nullable=False,
        default=UserStatus.PENDING,
        index=True
    )
    is_verified = Column(Boolean, nullable=False, default=False)

    # MFA (Multi-Factor Authentication)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(String(255), nullable=True)  # TOTP secret
    backup_codes = Column(ARRAY(String), nullable=True)  # Backup MFA codes

    # Login tracking
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_failed_login = Column(DateTime(timezone=True), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Token versioning for revocation
    token_version = Column(Integer, nullable=False, default=0)

    # Multi-tenancy
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # NULL = super-admin

    # Password management
    password_changed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    force_password_change = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_users_email_lower', 'email'),
        Index('idx_users_role_status', 'role', 'status'),
        Index('idx_users_status_active', 'status'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role}, status={self.status})>"

    def is_locked(self):
        """Check if account is locked"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return self.status == UserStatus.LOCKED

    def has_role(self, *roles):
        """Check if user has any of the specified roles"""
        return self.role in roles

    def is_privileged(self):
        """Check if user has privileged role (requires MFA)"""
        return self.role in [UserRole.SUPERVISOR, UserRole.REGIONAL_MGR, UserRole.ADMIN, UserRole.OWNER]

    def can_perform_transaction(self):
        """Check if user can perform card transactions"""
        return self.status == UserStatus.ACTIVE and not self.is_locked()

    def can_approve_refund(self):
        """Check if user can approve refunds"""
        return (
            self.status == UserStatus.ACTIVE
            and not self.is_locked()
            and self.role in [UserRole.SUPERVISOR, UserRole.REGIONAL_MGR, UserRole.ADMIN, UserRole.OWNER]
        )

    def can_manage_staff(self):
        """Check if user can manage staff"""
        return (
            self.status == UserStatus.ACTIVE
            and not self.is_locked()
            and self.role in [UserRole.REGIONAL_MGR, UserRole.ADMIN, UserRole.OWNER]
        )

    def can_configure_system(self):
        """Check if user can configure system settings"""
        return (
            self.status == UserStatus.ACTIVE
            and not self.is_locked()
            and self.role in [UserRole.ADMIN, UserRole.OWNER]
        )

    def increment_failed_login(self):
        """Increment failed login counter"""
        current = self.failed_login_attempts or 0
        self.failed_login_attempts = current + 1
        self.last_failed_login = datetime.utcnow()

        # Lock after 5 failed attempts (from config)
        from app.config import settings
        if current + 1 >= settings.max_login_attempts:
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_duration_minutes)
            self.status = UserStatus.LOCKED

    def reset_failed_login(self):
        """Reset failed login counter"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        if self.status == UserStatus.LOCKED:
            self.locked_until = None
            self.status = UserStatus.ACTIVE


# Add timedelta import for date calculations
from datetime import timedelta