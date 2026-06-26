"""Refresh token blacklist model"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index

from app.database import Base


class RefreshTokenBlacklist(Base):
    """
    Blacklist for revoked refresh tokens.

    When a user logs out or their token is compromised,
    the refresh token hash is added to this table to prevent reuse.
    """
    __tablename__ = "refresh_token_blacklist"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Token hash (SHA256 of the refresh token)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    # When token was revoked
    revoked_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # When token expires (for cleanup)
    expires_at = Column(DateTime, nullable=False, index=True)

    # User who owned the token
    user_id = Column(String, nullable=False, index=True)

    # Reason for revocation
    revocation_reason = Column(String(50), nullable=True)  # LOGOUT, COMPROMISED, PASSWORD_CHANGE

    def __repr__(self):
        return f"<RefreshTokenBlacklist(id={self.id}, user_id={self.user_id}, reason={self.revocation_reason})>"

    # Indexes for performance
    __table_args__ = (
        Index('idx_refresh_blacklist_token_hash', 'token_hash'),
        Index('idx_refresh_blacklist_expires_at', 'expires_at'),
        Index('idx_refresh_blacklist_user_id', 'user_id'),
    )