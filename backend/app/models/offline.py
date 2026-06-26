"""Offline signed token model for device-side play without connectivity"""
from sqlalchemy import Column, String, DateTime, Integer, UUID, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid

from app.database import Base
from app.models.card import Card
from app.models.user import User


class OfflineToken(Base):
    """
    Signed JWT tokens for offline play.

    These tokens allow readers to operate without internet connectivity:
    - Tokens are signed with private key, verified with public key
    - Include balance, expiration, and card UID
    - Stored server-side for revocation and reconciliation
    - Devices cache valid tokens for offline operation

    Security Model:
    - Tokens are short-lived (1-4 hours)
    - Include device fingerprint for device binding
    - Server maintains revocation list
    - Tokens expire and require refresh

    Token Structure:
    {
      "card_uid": "CARD-12345678",
      "company_id": "...",
      "balance": 150.00,
      "device_id": "...",
      "issued_at": "2026-06-26T12:00:00Z",
      "expires_at": "2026-06-26T16:00:00Z",
      "token_version": 1
    }
    """
    __tablename__ = "offline_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Token details
    token_id = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID claim
    card_uid = Column(String(255), nullable=False, index=True)

    # Multi-tenancy
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Token data
    balance = Column(Integer, nullable=False)  # Balance in integer (cents)
    issued_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Device binding
    device_id = Column(String(255), nullable=True, index=True)  # Device fingerprint

    # Revocation tracking
    token_version = Column(Integer, nullable=False, default=1)
    is_revoked = Column(Integer, nullable=False, default=0)  # 0 = active, 1 = revoked
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    revocation_reason = Column(String(500), nullable=True)

    # Usage tracking
    used_count = Column(Integer, nullable=False, default=0)  # Number of times used
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_offline_tokens_card_active', 'card_uid', 'is_revoked'),
        Index('idx_offline_tokens_device_active', 'device_id', 'is_revoked'),
        Index('idx_offline_tokens_expiry', 'expires_at', 'is_revoked'),
    )

    def __repr__(self):
        return f"<OfflineToken(id={self.id}, card_uid={self.card_uid}, balance={self.balance}, revoked={self.is_revoked})>"

    def is_expired(self):
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired() and self.is_revoked == 0

    def to_dict(self):
        """Convert token to dictionary"""
        return {
            "id": str(self.id),
            "token_id": self.token_id,
            "card_uid": self.card_uid,
            "company_id": str(self.company_id) if self.company_id else None,
            "balance": self.balance,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "device_id": self.device_id,
            "token_version": self.token_version,
            "is_revoked": bool(self.is_revoked),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by": str(self.revoked_by) if self.revoked_by else None,
            "revocation_reason": self.revocation_reason,
            "used_count": self.used_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat()
        }


class OfflineTransaction(Base):
    """
    Transactions created offline and queued for sync.

    When devices operate offline, transactions are:
    1. Created locally with device-signed data
    2. Queued for sync when connectivity returns
    3. Verified against server-side balance
    4. Applied or rejected based on validity

    This table tracks all offline transactions awaiting sync.
    """
    __tablename__ = "offline_transactions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Card details
    card_uid = Column(String(255), nullable=False, index=True)

    # Multi-tenancy
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Transaction data (from device)
    amount = Column(Integer, nullable=False)  # Amount in integer (cents)
    transaction_type = Column(String(50), nullable=False)  # DEDUCT, REFUND
    device_id = Column(String(255), nullable=False, index=True)
    offline_token_id = Column(String(255), nullable=False)  # JWT ID used

    # Device metadata
    machine_id = Column(String(255), nullable=True)
    location_id = Column(String(255), nullable=True)
    device_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Sync status
    sync_status = Column(String(50), nullable=False, default="PENDING")  # PENDING, SYNCED, REJECTED
    synced_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(500), nullable=True)

    # Server-side reference (after sync)
    server_transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id'), nullable=True)

    # Verification
    device_signature = Column(String(255), nullable=True)  # Device-signed hash
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(String(50), nullable=True)  # PENDING, VERIFIED, FAILED

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_offline_tx_sync_status', 'sync_status', 'created_at'),
        Index('idx_offline_tx_device_pending', 'device_id', 'sync_status'),
        Index('idx_offline_tx_company_pending', 'company_id', 'sync_status'),
    )

    def __repr__(self):
        return f"<OfflineTransaction(id={self.id}, card_uid={self.card_uid}, amount={self.amount}, status={self.sync_status})>"

    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            "id": str(self.id),
            "card_uid": self.card_uid,
            "company_id": str(self.company_id) if self.company_id else None,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "device_id": self.device_id,
            "offline_token_id": self.offline_token_id,
            "machine_id": self.machine_id,
            "location_id": self.location_id,
            "device_timestamp": self.device_timestamp.isoformat() if self.device_timestamp else None,
            "sync_status": self.sync_status,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "rejection_reason": self.rejection_reason,
            "server_transaction_id": str(self.server_transaction_id) if self.server_transaction_id else None,
            "device_signature": self.device_signature,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }