"""Balance ledger model for tracking all balance changes"""
from sqlalchemy import Column, String, DECIMAL, DateTime, Integer, ForeignKey, Index, UUID
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.models.card import Transaction


class BalanceLedger(Base):
    """
    Immutable ledger tracking all balance changes.
    
    This table provides:
    - Complete audit trail of balance changes
    - Transaction reconciliation
    - Balance rollback capability
    - Financial compliance
    
    Key features:
    - Every balance change is logged here
    - Before/after snapshots for every transaction
    - Links to original transaction
    - Never updated, only appended (immutable)
    - Supports financial audits and disputes
    """
    __tablename__ = "balance_ledger"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Card being modified
    card_uid = Column(String(255), nullable=False, index=True)

    # Multi-tenancy
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Transaction reference
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('transactions.id'), nullable=True, index=True)

    # Balance change details
    amount = Column(DECIMAL(10, 2), nullable=False)
    balance_before = Column(DECIMAL(10, 2), nullable=False)
    balance_after = Column(DECIMAL(10, 2), nullable=False)
    operation_type = Column(String(50), nullable=False)  # ADD, DEDUCT, REFUND, ADJUSTMENT

    # Context
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    notes = Column(String(500), nullable=True)

    # Metadata
    reason_code = Column(String(50), nullable=True)  # For disputes and reversals
    extra_metadata = Column(JSONB, nullable=True)  # Flexible context data

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    transaction = relationship("Transaction", backref="ledger_entries")
    user = relationship("User", foreign_keys=[user_id], backref="ledger_actions")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_ledger_card_date', 'card_uid', 'created_at', 'operation_type'),
        Index('idx_ledger_company_date', 'company_id', 'created_at'),
        Index('idx_ledger_transaction', 'transaction_id'),
        Index('idx_ledger_user_date', 'user_id', 'created_at'),
        Index('idx_ledger_reason_code', 'reason_code'),
    )

    def __repr__(self):
        return f"<BalanceLedger(id={self.id}, card_uid={self.card_uid}, amount={self.amount}, type={self.operation_type})>"

    def to_dict(self):
        """Convert ledger entry to dictionary"""
        return {
            "id": str(self.id),
            "card_uid": self.card_uid,
            "company_id": str(self.company_id) if self.company_id else None,
            "transaction_id": str(self.transaction_id) if self.transaction_id else None,
            "amount": float(self.amount),
            "balance_before": float(self.balance_before),
            "balance_after": float(self.balance_after),
            "operation_type": self.operation_type,
            "user_id": str(self.user_id) if self.user_id else None,
            "notes": self.notes,
            "reason_code": self.reason_code,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat()
        }


class BalanceSnapshot(Base):
    """
    Periodic balance snapshots for historical reporting.
    
    Snapshots are taken at regular intervals (daily/hourly)
    to enable:
    - Historical balance queries
    - Period-end financial reporting
    - Balance trend analysis
    - Growth metrics
    
    These are separate from ledger entries because:
    - Ledger = every individual change
    - Snapshots = aggregated state at point in time
    - More efficient for large-scale queries
    """
    __tablename__ = "balance_snapshots"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Card being snapshot
    card_uid = Column(String(255), nullable=False, index=True)

    # Multi-tenancy
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Snapshot details
    balance = Column(DECIMAL(10, 2), nullable=False)
    snapshot_type = Column(String(50), nullable=False)  # HOURLY, DAILY, WEEKLY, MONTHLY

    # Statistics
    total_transactions = Column(Integer, nullable=False, default=0)
    total_additions = Column(DECIMAL(10, 2), nullable=False, default=0)
    total_deductions = Column(DECIMAL(10, 2), nullable=False, default=0)
    total_refunds = Column(DECIMAL(10, 2), nullable=False, default=0)

    # Timestamp
    snapshot_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_snapshots_card_date', 'card_uid', 'snapshot_at'),
        Index('idx_snapshots_company_type', 'company_id', 'snapshot_type', 'snapshot_at'),
    )

    def __repr__(self):
        return f"<BalanceSnapshot(id={self.id}, card_uid={self.card_uid}, balance={self.balance}, type={self.snapshot_type})>"

    def to_dict(self):
        """Convert snapshot to dictionary"""
        return {
            "id": str(self.id),
            "card_uid": self.card_uid,
            "company_id": str(self.company_id) if self.company_id else None,
            "balance": float(self.balance),
            "snapshot_type": self.snapshot_type,
            "total_transactions": self.total_transactions,
            "total_additions": float(self.total_additions),
            "total_deductions": float(self.total_deductions),
            "total_refunds": float(self.total_refunds),
            "snapshot_at": self.snapshot_at.isoformat()
        }