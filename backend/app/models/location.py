"""Location model for arcade location management"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class LocationStatus(str, enum.Enum):
    """Location status"""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    MAINTENANCE = "MAINTENANCE"
    TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"


class Location(Base):
    """
    Location model for arcade branches/sites.
    
    Each arcade location has its own staff, machines, and card transactions.
    """
    __tablename__ = "locations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Company/Region
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    region_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Location details
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, unique=True, index=True)

    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)

    # Settings
    timezone = Column(String(50), default='UTC')
    currency = Column(String(10), default='EGP')

    # Status
    status = Column(
        String(20),
        nullable=False,
        default=LocationStatus.ACTIVE,
        index=True
    )

    # Contact info
    manager_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    manager_name = Column(String(100), nullable=True)

    # Operating hours
    opens_at = Column(String(10), nullable=True)  # HH:MM format
    closes_at = Column(String(10), nullable=True)  # HH:MM format

    # Metadata
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    opened_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_locations_name', 'name'),
        Index('idx_locations_city', 'city'),
        Index('idx_locations_status', 'status'),
        Index('idx_locations_region', 'region_id'),
    )

    def __repr__(self):
        return f"<Location(id={self.id}, name={self.name}, city={self.city})>"

    @property
    def full_address(self):
        """Get full address"""
        parts = [self.address, self.city, self.state, self.postal_code]
        return ", ".join([p for p in parts if p])

    @property
    def is_active(self):
        """Check if location is active"""
        return self.status == LocationStatus.ACTIVE

    def is_open(self):
        """Check if location is currently open"""
        if not self.is_active:
            return False
        if not self.opens_at or not self.closes_at:
            return True  # Assume open if no hours set
        # TODO: Implement timezone-aware time comparison
        return True

    def close_location(self):
        """Close the location"""
        self.status = LocationStatus.CLOSED
        self.updated_at = datetime.utcnow()

    def open_location(self):
        """Open the location"""
        self.status = LocationStatus.ACTIVE
        self.updated_at = datetime.utcnow()