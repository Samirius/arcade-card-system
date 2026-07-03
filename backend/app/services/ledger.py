"""Balance ledger service for server-authoritative balance management"""
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.models.balance import BalanceLedger, BalanceSnapshot
from app.models.card import Card


class BalanceLedgerService:
    """
    Service for server-authoritative balance management.
    
    This service ensures:
    - All balance changes are logged to the ledger
    - Atomic operations prevent race conditions
    - Full audit trail for compliance
    - Rollback capability for disputes
    - Reconciliation support
    """

    @staticmethod
    def record_ledger_entry(
        db: Session,
        card_uid: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        operation_type: str,
        user_id: Optional[str],
        transaction_id: Optional[str],
        notes: Optional[str] = None,
        reason_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BalanceLedger:
        """
        Record a balance change to the ledger.

        Args:
            db: Database session
            card_uid: Card UID
            amount: Amount changed (positive for add, negative for deduct)
            balance_before: Balance before change
            balance_after: Balance after change
            operation_type: Type of operation (ADD, DEDUCT, REFUND, ADJUSTMENT)
            user_id: User who performed the operation
            transaction_id: Related transaction ID
            notes: Optional notes
            reason_code: For disputes and reversals
            metadata: Flexible context data

        Returns:
            Created ledger entry
        """
        # Get card for company_id
        card = db.query(Card).filter(Card.card_uid == card_uid).first()
        company_id = card.company_id if card else None

        # Create ledger entry
        ledger_entry = BalanceLedger(
            card_uid=card_uid,
            company_id=company_id,
            transaction_id=transaction_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            operation_type=operation_type,
            user_id=user_id,
            notes=notes,
            reason_code=reason_code,
            extra_metadata=metadata if metadata else None,
            created_at=datetime.utcnow()
        )

        db.add(ledger_entry)
        db.commit()
        db.refresh(ledger_entry)

        return ledger_entry

    @staticmethod
    def add_balance(
        db: Session,
        card_uid: str,
        amount: Decimal,
        user_id: str,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add balance to a card with ledger entry.

        Args:
            db: Database session
            card_uid: Card UID
            amount: Amount to add (must be positive)
            user_id: User performing operation
            notes: Optional notes
            metadata: Optional context data

        Returns:
            Dictionary with result and ledger entry
        """
        if amount <= 0:
            raise ValueError("Amount must be positive for addition")

        # Lock card for atomic operation
        card = db.query(Card).filter(
            Card.card_uid == card_uid
        ).with_for_update().first()

        if not card:
            raise ValueError(f"Card {card_uid} not found")

        balance_before = card.balance
        card.add_balance(amount)
        balance_after = card.balance
        card.last_transaction_at = datetime.utcnow()

        # Record ledger entry
        ledger_entry = BalanceLedgerService.record_ledger_entry(
            db=db,
            card_uid=card_uid,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            operation_type="ADD",
            user_id=user_id,
            transaction_id=None,
            notes=notes or f"Added {amount} credits",
            metadata=metadata
        )

        return {
            "success": True,
            "card_uid": card_uid,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "ledger_entry": ledger_entry.to_dict()
        }

    @staticmethod
    def deduct_balance(
        db: Session,
        card_uid: str,
        amount: Decimal,
        user_id: str,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deduct balance from a card with ledger entry.

        Args:
            db: Database session
            card_uid: Card UID
            amount: Amount to deduct (must be positive)
            user_id: User performing operation
            notes: Optional notes
            metadata: Optional context data

        Returns:
            Dictionary with result and ledger entry

        Raises:
            ValueError: If insufficient balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive for deduction")

        # Lock card for atomic operation
        card = db.query(Card).filter(
            Card.card_uid == card_uid
        ).with_for_update().first()

        if not card:
            raise ValueError(f"Card {card_uid} not found")

        balance_before = card.balance

        if balance_before < amount:
            raise ValueError(f"Insufficient balance: {balance_before}, attempting to deduct {amount}")

        card.deduct_balance(amount)
        balance_after = card.balance
        card.last_transaction_at = datetime.utcnow()

        # Record ledger entry
        ledger_entry = BalanceLedgerService.record_ledger_entry(
            db=db,
            card_uid=card_uid,
            amount=-amount,  # Negative for deduction
            balance_before=balance_before,
            balance_after=balance_after,
            operation_type="DEDUCT",
            user_id=user_id,
            transaction_id=None,
            notes=notes or f"Deducted {amount} credits",
            metadata=metadata
        )

        return {
            "success": True,
            "card_uid": card_uid,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "ledger_entry": ledger_entry.to_dict()
        }

    @staticmethod
    def get_ledger_history(
        db: Session,
        card_uid: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        operation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get ledger history for a card.

        Args:
            db: Database session
            card_uid: Card UID
            start_date: Start date filter
            end_date: End date filter
            operation_type: Filter by operation type
            limit: Maximum number of entries

        Returns:
            List of ledger entries
        """
        query = db.query(BalanceLedger).filter(
            BalanceLedger.card_uid == card_uid
        )

        if start_date:
            query = query.filter(BalanceLedger.created_at >= start_date)

        if end_date:
            query = query.filter(BalanceLedger.created_at <= end_date)

        if operation_type:
            query = query.filter(BalanceLedger.operation_type == operation_type)

        ledger_entries = query.order_by(
            BalanceLedger.created_at.desc()
        ).limit(limit).all()

        return [entry.to_dict() for entry in ledger_entries]

    @staticmethod
    def reconcile_balance(
        db: Session,
        card_uid: str
    ) -> Dict[str, Any]:
        """
        Reconcile balance by recalculating from ledger.

        Args:
            db: Database session
            card_uid: Card UID

        Returns:
            Dictionary with reconciliation results
        """
        # Get all ledger entries for this card
        ledger_entries = db.query(BalanceLedger).filter(
            BalanceLedger.card_uid == card_uid
        ).order_by(BalanceLedger.created_at.asc()).all()

        # Get current card balance
        card = db.query(Card).filter(Card.card_uid == card_uid).first()

        if not card:
            return {
                "card_uid": card_uid,
                "reconciled_balance": 0,
                "current_balance": None,
                "discrepancy": 0,
                "status": "CARD_NOT_FOUND"
            }

        # Calculate balance from ledger
        reconciled_balance = Decimal("0.00")
        for entry in ledger_entries:
            reconciled_balance += entry.amount

        current_balance = card.balance
        discrepancy = abs(reconciled_balance - current_balance)

        # Create reconciliation record
        reconciliation = {
            "card_uid": card_uid,
            "reconciled_balance": float(reconciled_balance),
            "current_balance": float(current_balance),
            "discrepancy": float(discrepancy),
            "total_ledger_entries": len(ledger_entries),
            "status": "MATCHED" if discrepancy == 0 else "DISCREPANCY",
            "last_ledger_entry": ledger_entries[-1].to_dict() if ledger_entries else None
        }

        return reconciliation

    @staticmethod
    def create_snapshot(
        db: Session,
        card_uid: str,
        snapshot_type: str = "DAILY"
    ) -> BalanceSnapshot:
        """
        Create a balance snapshot.

        Args:
            db: Database session
            card_uid: Card UID
            snapshot_type: Type of snapshot (HOURLY, DAILY, WEEKLY, MONTHLY)

        Returns:
            Created snapshot
        """
        # Get card for company_id
        card = db.query(Card).filter(Card.card_uid == card_uid).first()
        if not card:
            raise ValueError(f"Card {card_uid} not found")

        company_id = card.company_id

        # Get ledger stats since last snapshot
        last_snapshot = db.query(BalanceSnapshot).filter(
            BalanceSnapshot.card_uid == card_uid,
            BalanceSnapshot.snapshot_type == snapshot_type
        ).order_by(BalanceSnapshot.snapshot_at.desc()).first()

        since_date = last_snapshot.snapshot_at if last_snapshot else datetime.min

        ledger_entries = db.query(BalanceLedger).filter(
            BalanceLedger.card_uid == card_uid,
            BalanceLedger.created_at >= since_date
        ).all()

        # Calculate stats
        total_transactions = len(ledger_entries)
        total_additions = sum(
            entry.amount for entry in ledger_entries if entry.operation_type == "ADD"
        )
        total_deductions = sum(
            abs(entry.amount) for entry in ledger_entries if entry.operation_type == "DEDUCT"
        )
        total_refunds = sum(
            entry.amount for entry in ledger_entries if entry.operation_type == "REFUND"
        )

        # Create snapshot
        snapshot = BalanceSnapshot(
            card_uid=card_uid,
            company_id=company_id,
            balance=card.balance,
            snapshot_type=snapshot_type,
            total_transactions=total_transactions,
            total_additions=total_additions,
            total_deductions=total_deductions,
            total_refunds=total_refunds,
            snapshot_at=datetime.utcnow()
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return snapshot

    @staticmethod
    def rollback_transaction(
        db: Session,
        card_uid: str,
        transaction_id: str,
        user_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Rollback a transaction by reversing balance changes.

        Args:
            db: Database session
            card_uid: Card UID
            transaction_id: Transaction ID to rollback
            user_id: User performing rollback
            reason: Reason for rollback

        Returns:
            Dictionary with rollback result
        """
        # Get ledger entries for this transaction
        ledger_entries = db.query(BalanceLedger).filter(
            BalanceLedger.transaction_id == transaction_id,
            BalanceLedger.card_uid == card_uid
        ).order_by(BalanceLedger.created_at.desc()).all()

        if not ledger_entries:
            raise ValueError(f"No ledger entries found for transaction {transaction_id}")

        # Lock card for atomic operation
        card = db.query(Card).filter(
            Card.card_uid == card_uid
        ).with_for_update().first()

        if not card:
            raise ValueError(f"Card {card_uid} not found")

        # Reverse each ledger entry (in reverse chronological order)
        reversed_entries = []
        for entry in reversed(ledger_entries):
            # Reverse the balance change
            if entry.operation_type == "ADD":
                card.deduct_balance(entry.amount)
                new_operation = "DEDUCT"
            elif entry.operation_type == "DEDUCT":
                card.add_balance(abs(entry.amount))
                new_operation = "ADD"
            elif entry.operation_type == "REFUND":
                # Refund needs special handling - maybe restore original state
                card.add_balance(abs(entry.amount))
                new_operation = "ADD"
            else:
                continue  # Skip unknown operations

            # Create reversal ledger entry
            reversal_entry = BalanceLedgerService.record_ledger_entry(
                db=db,
                card_uid=card_uid,
                amount=-entry.amount,  # Reverse amount
                balance_before=entry.balance_after,
                balance_after=card.balance,
                operation_type=f"{new_operation}_ROLLBACK",
                user_id=user_id,
                transaction_id=None,
                notes=f"Rolled back transaction {transaction_id}: {reason}",
                reason_code="ROLLBACK",
                metadata={
                    "original_transaction_id": str(transaction_id),
                    "original_ledger_entry_id": str(entry.id),
                    "original_operation": entry.operation_type,
                    "original_amount": float(entry.amount),
                    "rollback_reason": reason
                }
            )

            reversed_entries.append(reversal_entry.to_dict())

        card.last_transaction_at = datetime.utcnow()

        return {
            "success": True,
            "card_uid": card_uid,
            "original_transaction_id": transaction_id,
            "entries_rolled_back": len(ledger_entries),
            "reversal_entries": reversed_entries,
            "final_balance": float(card.balance),
            "reason": reason
        }