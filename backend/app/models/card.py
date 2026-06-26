"""Card model for arcade card management"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, DECIMAL, Enum as SQLEnum, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class CardType(str, enum.Enum):
    """Card types with different pricing and features"""
    REGULAR = "REGULAR"           # Standard pricing
    VIP = "VIP"                   # Discounted rates, priority
    STAFF = "STAFF"               # Free play, admin access
    TEST = "TEST"                 # Testing card


class CardStatus(str, enum.Enum):
    """Card status"""
    ACTIVE = "ACTIVE"             # Card is active and usable
    INACTIVE = "INACTIVE"         # Card temporarily disabled
    LOST = "LOST"                 # Card reported lost
    STOLEN = "STOLEN"             # Card reported stolen
    DAMAGED = "DAMAGED"           # Card is damaged


class Card(Base):
    """
    Card model for arcade card management.

    Card Types:
    - REGULAR: Standard pricing
    - VIP: Discounted rates, priority
    - STAFF: Free play, admin access
    - TEST: Testing card
    """
    __tablename__ = "cards"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Card identification
    card_uid = Column(String(255), unique=True, nullable=False, index=True)

    # Owner information
    owner = Column(String(100), nullable=False)

    # Card type and status
    card_type = Column(
        SQLEnum(CardType, name="card_type", create_type=True),
        nullable=False,
        default=CardType.REGULAR,
        index=True
    )
    status = Column(
        SQLEnum(CardStatus, name="card_status", create_type=True),
        nullable=False,
        default=CardStatus.ACTIVE,
        index=True
    )

    # Balance
    balance = Column(DECIMAL(10, 2), nullable=False, default=0.00)

    # Notes and metadata
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Last transaction tracking
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_cards_uid_type', 'card_uid', 'card_type'),
        Index('idx_cards_owner_status', 'owner', 'status'),
        Index('idx_cards_type_status', 'card_type', 'status'),
    )

    def __repr__(self):
        return f"<Card(id={self.id}, card_uid={self.card_uid}, owner={self.owner}, type={self.card_type})>"

    def is_active(self):
        """Check if card is active"""
        return self.status == CardStatus.ACTIVE

    def can_transact(self):
        """Check if card can perform transactions"""
        return self.is_active()

    def add_balance(self, amount):
        """Add balance to card"""
        self.balance += amount
        self.updated_at = datetime.utcnow()

    def deduct_balance(self, amount):
        """Deduct balance from card"""
        self.balance -= amount
        self.updated_at = datetime.utcnow()

    def get_remaining_play(self, rate_per_minute):
        """Get remaining play time in minutes"""
        if rate_per_minute <= 0:
            return 0
        return float(self.balance / rate_per_minute)


class Transaction(Base):
    """
    Transaction model for tracking card balance changes.

    Transaction Types:
    - ADD: Adding credits to card
    - DEDUCT: Using credits for play
    - REFUND: Refunding credits
    """
    __tablename__ = "transactions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Card reference
    card_uid = Column(String(255), nullable=False, index=True)

    # Transaction details
    amount = Column(DECIMAL(10, 2), nullable=False)
    transaction_type = Column(String(20), nullable=False, index=True)
    payment_method = Column(String(50), nullable=True)

    # User who performed transaction (optional)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    # Additional information
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    # Relationship to user
    user = relationship("User", backref="transactions")

    # Indexes
    __table_args__ = (
        Index('idx_transactions_card_date', 'card_uid', 'created_at'),
        Index('idx_transactions_type_date', 'transaction_type', 'created_at'),
        Index('idx_transactions_user_date', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, card_uid={self.card_uid}, amount={self.amount}, type={self.transaction_type})>"

    def is_credit(self):
        """Check if transaction adds credit"""
        return self.transaction_type == "ADD"

    def is_debit(self):
        """Check if transaction deducts credit"""
        return self.transaction_type in ["DEDUCT", "REFUND"]