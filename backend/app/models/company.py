"""Company and Region models for multi-tenant architecture"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tiers"""
    BASIC = "BASIC"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


class Company(Base):
    """
    Company model for multi-tenant arcade management.
    
    Each company can have multiple locations and users.
    """
    __tablename__ = "companies"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Company details
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, unique=True, index=True)

    # Contact
    email = Column(String(255), nullable=True, unique=True)
    phone = Column(String(20), nullable=True)

    # Subscription
    subscription_tier = Column(
        String(50),
        nullable=False,
        default=SubscriptionTier.STANDARD,
        index=True
    )
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Settings (JSONB for flexibility)
    settings = Column(JSON, nullable=True, default={})

    # Metadata
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_companies_name', 'name'),
        Index('idx_companies_tier', 'subscription_tier'),
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name}, tier={self.subscription_tier})>"

    @property
    def is_subscription_active(self):
        """Check if subscription is active"""
        if not self.subscription_expires_at:
            return True
        return datetime.utcnow() < self.subscription_expires_at

    @property
    def days_until_expiry(self):
        """Days until subscription expires"""
        if not self.subscription_expires_at:
            return 999
        delta = self.subscription_expires_at - datetime.utcnow()
        return delta.days


class Region(Base):
    """
    Region model for geographical organization.
    
    Each company can have multiple regions.
    Each region can have multiple locations.
    """
    __tablename__ = "regions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Company
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Region details
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, unique=True, index=True)

    # Manager
    manager_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    manager_name = Column(String(100), nullable=True)

    # Geography
    country = Column(String(50), nullable=True)
    timezone = Column(String(50), default='UTC')

    # Metadata
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_regions_company', 'company_id'),
        Index('idx_regions_name', 'name'),
        Index('idx_regions_manager', 'manager_id'),
    )

    def __repr__(self):
        return f"<Region(id={self.id}, name={self.name}, country={self.country})>"

    @property
    def full_name(self):
        """Get full region name with country"""
        if self.country:
            return f"{self.name}, {self.country}"
        return self.name