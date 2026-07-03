"""Device / reader model for the DEVICE money tier.

A Device is a physical card reader / point-of-sale terminal bound to a single
company (tenant). It authenticates to the money-path endpoints with a bearer
device_token (only its SHA-256 hash is persisted).

Security note:
    mTLS / X.509 client certificates are the PRODUCTION upgrade for device
    identity. The bearer device_token implemented here is the pragmatic pilot
    credential: simple to provision, revocable, and hash-at-rest.
"""
import uuid
from datetime import datetime
import enum

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Index, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DeviceStatus(str, enum.Enum):
    """Device lifecycle status."""
    ACTIVE = "ACTIVE"        # Enrolled and able to transact
    REVOKED = "REVOKED"      # Token revoked, cannot transact
    INACTIVE = "INACTIVE"    # Temporarily disabled


class Device(Base):
    """
    A physical card reader / terminal bound to a company (tenant).

    Authenticates to money-path endpoints via ``Authorization: Bearer <token>``.
    Only the SHA-256 hash of the token is stored (``device_token_hash``); the
    plaintext token is returned exactly once, at enrollment time.
    """
    __tablename__ = "devices"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Multi-tenancy — every device belongs to exactly one company
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Venue / human-readable label for the device
    label = Column(String(255), nullable=False)
    venue = Column(String(255), nullable=True)

    # Bearer credential (SHA-256 hex of the plaintext token, never the token itself)
    device_token_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Status
    status = Column(
        SQLEnum(DeviceStatus, name="device_status", create_type=True),
        nullable=False,
        default=DeviceStatus.ACTIVE,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_devices_company_status", "company_id", "status"),
    )

    def __repr__(self):
        return f"<Device(id={self.id}, label={self.label}, company_id={self.company_id}, status={self.status})>"

    def is_active(self) -> bool:
        return self.status == DeviceStatus.ACTIVE

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": str(self.company_id) if self.company_id else None,
            "label": self.label,
            "venue": self.venue,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class ChargeIdempotency(Base):
    """
    Persisted idempotency record for the money path.

    Keyed uniquely on (company_id, client_txn_id). A repeat charge with the same
    client_txn_id returns the stored result WITHOUT debiting the card again.
    ``result_json`` stores the canonical response so replays are byte-identical.
    """
    __tablename__ = "charge_idempotency"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Idempotency key parts
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    client_txn_id = Column(String(255), nullable=False, index=True)

    # Denormalized context
    card_uid = Column(String(255), nullable=True, index=True)
    device_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Result of the original processing
    result = Column(String(20), nullable=False)  # approved | declined
    server_txn_id = Column(String(255), nullable=False)
    balance_after_cents = Column(BigInteger, nullable=True)
    price_cents = Column(BigInteger, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        # Enforce idempotency at the database level.
        Index("uq_charge_idem_company_client", "company_id", "client_txn_id", unique=True),
    )

    def __repr__(self):
        return f"<ChargeIdempotency(company_id={self.company_id}, client_txn_id={self.client_txn_id}, result={self.result})>"


class HouseAccount(Base):
    """
    Per-company internal ledger account (e.g. ``offline_shortfall``).

    Used to record money that could not be collected from a card — for example
    when an offline reader authorized play the card could not actually cover
    (offline overspend). The shortfall accrues here as a running balance (cents).
    """
    __tablename__ = "house_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_type = Column(String(64), nullable=False, index=True)  # e.g. offline_shortfall

    # Running balance in integer cents.
    balance_cents = Column(BigInteger, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("uq_house_account_company_type", "company_id", "account_type", unique=True),
    )

    def __repr__(self):
        return f"<HouseAccount(company_id={self.company_id}, type={self.account_type}, balance_cents={self.balance_cents})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "company_id": str(self.company_id) if self.company_id else None,
            "account_type": self.account_type,
            "balance_cents": int(self.balance_cents) if self.balance_cents is not None else 0,  # noqa: E501
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
