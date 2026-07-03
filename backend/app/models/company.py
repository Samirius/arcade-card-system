"""Company (tenant) model for multi-tenancy"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from enum import Enum

from app.database import Base


class CompanyPlan(str, Enum):
    """Subscription plan types"""
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class CompanyStatus(str, Enum):
    """Company status types"""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TRIAL = "TRIAL"
    INACTIVE = "INACTIVE"


class Company(Base):
    """
    Company (tenant) model.

    Each company represents a separate tenant in the multi-tenant system.
    A company can have multiple users, cards, and transactions.
    """
    __tablename__ = "companies"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Company information
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)  # URL-friendly name

    # Contact information
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    # Address
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Business information
    business_type = Column(String(100), nullable=True)  # e.g., "FEC", "Arcade", "Family Entertainment"
    tax_id = Column(String(50), nullable=True)

    # Status and configuration
    status = Column(String(20), nullable=False, default='ACTIVE', index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Plan and billing
    plan = Column(String(50), nullable=False, default='STARTER')  # STARTER, PRO, ENTERPRISE
    max_venues = Column(Integer, nullable=False, default=1)  # Max number of venues allowed
    max_users = Column(Integer, nullable=False, default=10)  # Max users allowed

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Indexes
    __table_args__ = (
        Index('idx_companies_name', 'name'),
        Index('idx_companies_slug', 'slug'),
        Index('idx_companies_status', 'status'),
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name}, slug={self.slug}, status={self.status})>"

    def is_active_company(self):
        """Check if company is active"""
        return self.is_active and self.status == 'ACTIVE'

    def has_soft_deleted(self):
        """Check if company is soft deleted"""
        return self.deleted_at is not None

    def can_add_user(self, db):
        """Check if company can add more users"""
        from app.models.user import User
        current_users = db.query(User).filter(User.company_id == self.id).count()
        return current_users < self.max_users

    def can_add_venue(self, db):
        """Check if company can add more venues"""
        # This will be used when Venue model exists
        return True  # TODO: Implement when Venue model exists