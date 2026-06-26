"""Customer model for arcade customer management"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Customer(Base):
    """
    Customer profile data for arcade customers.
    
    Customers represent people who own cards and visit the arcade.
    Separate from Users (who are staff/admin).
    """
    __tablename__ = "customers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User account (optional - if they want to login)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Contact information
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # Address
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)

    # Preferences
    preferred_language = Column(String(10), default='en')

    # Metadata
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_visit = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_customers_email', 'email'),
        Index('idx_customers_name', 'first_name', 'last_name'),
        Index('idx_customers_phone', 'phone'),
    )

    def __repr__(self):
        return f"<Customer(id={self.id}, name={self.full_name}, email={self.email})>"

    @property
    def full_name(self):
        """Get customer's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or "Unknown"

    def update_visit(self):
        """Update last visit timestamp"""
        self.last_visit = datetime.utcnow()
        self.updated_at = datetime.utcnow()