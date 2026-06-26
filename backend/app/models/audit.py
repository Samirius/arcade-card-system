"""Audit log model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class AuditAction(str, enum.Enum):
    """Audit action types"""
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRANSACTION = "TRANSACTION"
    REFUND = "REFUND"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    FAILED_LOGIN = "FAILED_LOGIN"


class AuditLog(Base):
    """Audit log for tracking user actions"""
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User who performed the action
    user_id = Column(UUID(as_uuid=True), nullable=True)

    # Action details
    action = Column(SQLEnum(AuditAction, name="audit_action"), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)

    # Change tracking
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Result
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_date', 'created_at'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"