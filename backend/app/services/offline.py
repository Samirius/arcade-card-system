"""Offline token management service for device-side play"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json

from jose import jwt
from app.models.offline import OfflineToken, OfflineTransaction
from app.models.card import Card
from app.models.user import User
from app.config import settings


class OfflineTokenService:
    """
    Service for managing offline tokens for device play.

    Features:
    - Issue signed tokens for offline play
    - Validate offline tokens on sync
    - Revoke tokens when balance changes
    - Queue offline transactions for sync
    - Process sync queue when connectivity returns
    """

    @staticmethod
    def _get_offline_token_secret():
        """Get secret key for signing offline tokens"""
        return getattr(settings, 'offline_token_secret', settings.secret_key)

    @staticmethod
    def issue_token(
        db: Session,
        card_uid: str,
        device_id: Optional[str] = None,
        ttl_hours: int = 4
    ) -> Dict[str, Any]:
        """
        Issue a signed offline token for a card.

        Args:
            db: Database session
            card_uid: Card UID
            device_id: Device fingerprint (optional, for device binding)
            ttl_hours: Time to live in hours (default: 4)

        Returns:
            Dictionary with token and metadata
        """
        # Get card details
        card = db.query(Card).filter(Card.card_uid == card_uid).first()
        if not card:
            raise ValueError(f"Card {card_uid} not found")

        if not card.is_active():
            raise ValueError(f"Card {card_uid} is not active")

        # Generate token ID
        token_id = str(uuid.uuid4())

        # Calculate expiry
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(hours=ttl_hours)

        # Create token payload
        payload = {
            "token_id": token_id,
            "card_uid": card_uid,
            "company_id": str(card.company_id) if card.company_id else None,
            "balance": int(card.balance * 100),  # Convert to cents (integer)
            "device_id": device_id,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "token_version": 1
        }

        # Sign token
        secret = OfflineTokenService._get_offline_token_secret()
        signed_token = jwt.encode(payload, secret, algorithm="HS256")

        # Store token in database
        offline_token = OfflineToken(
            token_id=token_id,
            card_uid=card_uid,
            company_id=card.company_id,
            balance=int(card.balance * 100),
            issued_at=issued_at,
            expires_at=expires_at,
            device_id=device_id,
            token_version=1,
            is_revoked=0,
            used_count=0
        )

        db.add(offline_token)
        db.commit()
        db.refresh(offline_token)

        return {
            "token": signed_token,
            "token_id": token_id,
            "card_uid": card_uid,
            "balance": float(card.balance),
            "expires_at": expires_at.isoformat(),
            "device_id": device_id,
            "ttl_hours": ttl_hours
        }

    @staticmethod
    def validate_token(
        db: Session,
        signed_token: str
    ) -> Dict[str, Any]:
        """
        Validate an offline token.

        Args:
            db: Database session
            signed_token: Signed JWT token

        Returns:
            Dictionary with validation result and payload
        """
        secret = OfflineTokenService._get_offline_token_secret()

        try:
            # Decode token
            payload = jwt.decode(signed_token, secret, algorithms=["HS256"])

            token_id = payload.get("token_id")
            card_uid = payload.get("card_uid")

            # Check if token exists in database
            offline_token = db.query(OfflineToken).filter(
                OfflineToken.token_id == token_id
            ).first()

            if not offline_token:
                return {
                    "valid": False,
                    "reason": "Token not found in database",
                    "payload": payload
                }

            # Check if token is revoked
            if offline_token.is_revoked == 1:
                return {
                    "valid": False,
                    "reason": "Token has been revoked",
                    "payload": payload
                }

            # Check if token is expired
            if offline_token.is_expired():
                return {
                    "valid": False,
                    "reason": "Token has expired",
                    "payload": payload
                }

            # Token is valid - increment usage count
            offline_token.used_count += 1
            offline_token.last_used_at = datetime.utcnow()
            db.commit()

            return {
                "valid": True,
                "token_id": token_id,
                "card_uid": card_uid,
                "balance": Decimal(str(payload.get("balance"))) / Decimal("100"),
                "expires_at": payload.get("expires_at"),
                "payload": payload
            }

        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "reason": "Token signature expired",
                "payload": None
            }
        except jwt.InvalidTokenError as e:
            return {
                "valid": False,
                "reason": f"Invalid token: {str(e)}",
                "payload": None
            }

    @staticmethod
    def revoke_token(
        db: Session,
        token_id: str,
        revoked_by: str,
        reason: str
    ) -> bool:
        """
        Revoke an offline token.

        Args:
            db: Database session
            token_id: Token ID to revoke
            revoked_by: User ID who is revoking
            reason: Reason for revocation

        Returns:
            True if revoked, False if not found
        """
        token = db.query(OfflineToken).filter(
            OfflineToken.token_id == token_id
        ).first()

        if not token:
            return False

        token.is_revoked = 1
        token.revoked_at = datetime.utcnow()
        token.revoked_by = uuid.UUID(revoked_by)
        token.revocation_reason = reason

        db.commit()

        return True

    @staticmethod
    def revoke_all_card_tokens(
        db: Session,
        card_uid: str,
        revoked_by: str,
        reason: str
    ) -> int:
        """
        Revoke all offline tokens for a card.

        Called when balance changes to invalidate old tokens.

        Args:
            db: Database session
            card_uid: Card UID
            revoked_by: User ID who is revoking
            reason: Reason for revocation

        Returns:
            Number of tokens revoked
        """
        tokens = db.query(OfflineToken).filter(
            OfflineToken.card_uid == card_uid,
            OfflineToken.is_revoked == 0
        ).all()

        count = 0
        for token in tokens:
            token.is_revoked = 1
            token.revoked_at = datetime.utcnow()
            token.revoked_by = uuid.UUID(revoked_by)
            token.revocation_reason = reason
            count += 1

        db.commit()

        return count

    @staticmethod
    def queue_offline_transaction(
        db: Session,
        card_uid: str,
        amount: int,
        transaction_type: str,
        device_id: str,
        offline_token_id: str,
        machine_id: Optional[str] = None,
        location_id: Optional[str] = None,
        device_timestamp: Optional[datetime] = None,
        device_signature: Optional[str] = None
    ) -> OfflineTransaction:
        """
        Queue an offline transaction for sync.

        Args:
            db: Database session
            card_uid: Card UID
            amount: Amount in cents
            transaction_type: DEDUCT, REFUND
            device_id: Device ID
            offline_token_id: Token ID used
            machine_id: Optional machine ID
            location_id: Optional location ID
            device_timestamp: Timestamp when transaction occurred
            device_signature: Device signature for verification

        Returns:
            Created offline transaction
        """
        # Get card for company_id
        card = db.query(Card).filter(Card.card_uid == card_uid).first()
        company_id = card.company_id if card else None

        offline_tx = OfflineTransaction(
            card_uid=card_uid,
            company_id=company_id,
            amount=amount,
            transaction_type=transaction_type,
            device_id=device_id,
            offline_token_id=offline_token_id,
            machine_id=machine_id,
            location_id=location_id,
            device_timestamp=device_timestamp,
            sync_status="PENDING",
            verification_status="PENDING",
            device_signature=device_signature
        )

        db.add(offline_tx)
        db.commit()
        db.refresh(offline_tx)

        return offline_tx

    @staticmethod
    def process_sync_queue(
        db: Session,
        device_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Process pending offline transactions from sync queue.

        Args:
            db: Database session
            device_id: Optional device ID filter
            limit: Maximum number to process

        Returns:
            Dictionary with processing results
        """
        # Get pending transactions
        query = db.query(OfflineTransaction).filter(
            OfflineTransaction.sync_status == "PENDING"
        )

        if device_id:
            query = query.filter(OfflineTransaction.device_id == device_id)

        pending_transactions = query.limit(limit).all()

        processed = {
            "total": len(pending_transactions),
            "synced": 0,
            "rejected": 0,
            "failed": 0,
            "details": []
        }

        from app.services.ledger import BalanceLedgerService

        for tx in pending_transactions:
            try:
                # Verify token is still valid
                token = db.query(OfflineToken).filter(
                    OfflineToken.token_id == tx.offline_token_id
                ).first()

                if not token or not token.is_valid():
                    # Token invalid - reject transaction
                    tx.sync_status = "REJECTED"
                    tx.rejection_reason = "Invalid or expired token"
                    processed["rejected"] += 1
                    processed["details"].append({
                        "tx_id": str(tx.id),
                        "status": "REJECTED",
                        "reason": "Invalid token"
                    })
                    db.commit()
                    continue

                # Get card and lock for atomic operation
                card = db.query(Card).filter(
                    Card.card_uid == tx.card_uid
                ).with_for_update().first()

                if not card:
                    tx.sync_status = "REJECTED"
                    tx.rejection_reason = "Card not found"
                    processed["rejected"] += 1
                    processed["details"].append({
                        "tx_id": str(tx.id),
                        "status": "REJECTED",
                        "reason": "Card not found"
                    })
                    db.commit()
                    continue

                # Process transaction
                amount = Decimal(str(tx.amount)) / Decimal("100")

                if tx.transaction_type == "DEDUCT":
                    if card.balance < amount:
                        tx.sync_status = "REJECTED"
                        tx.rejection_reason = "Insufficient balance"
                        processed["rejected"] += 1
                        processed["details"].append({
                            "tx_id": str(tx.id),
                            "status": "REJECTED",
                            "reason": "Insufficient balance"
                        })
                        db.commit()
                        continue

                    balance_before = card.balance
                    card.deduct_balance(amount)
                    balance_after = card.balance
                    card.last_transaction_at = datetime.utcnow()

                elif tx.transaction_type == "REFUND":
                    balance_before = card.balance
                    card.add_balance(amount)
                    balance_after = card.balance
                    card.last_transaction_at = datetime.utcnow()

                else:
                    tx.sync_status = "REJECTED"
                    tx.rejection_reason = f"Unknown transaction type: {tx.transaction_type}"
                    processed["rejected"] += 1
                    processed["details"].append({
                        "tx_id": str(tx.id),
                        "status": "REJECTED",
                        "reason": "Unknown transaction type"
                    })
                    db.commit()
                    continue

                # Record ledger entry
                ledger_entry = BalanceLedgerService.record_ledger_entry(
                    db=db,
                    card_uid=tx.card_uid,
                    amount=-amount if tx.transaction_type == "DEDUCT" else amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    operation_type=tx.transaction_type,
                    user_id=None,  # Offline transaction
                    transaction_id=None,
                    notes=f"Offline sync: {tx.transaction_type}",
                    metadata={
                        "device_id": tx.device_id,
                        "machine_id": tx.machine_id,
                        "location_id": tx.location_id,
                        "offline_tx_id": str(tx.id),
                        "device_timestamp": tx.device_timestamp.isoformat() if tx.device_timestamp else None
                    }
                )

                # Mark as synced
                tx.sync_status = "SYNCED"
                tx.synced_at = datetime.utcnow()
                tx.verification_status = "VERIFIED"
                tx.verified_at = datetime.utcnow()

                processed["synced"] += 1
                processed["details"].append({
                    "tx_id": str(tx.id),
                    "status": "SYNCED",
                    "ledger_entry_id": str(ledger_entry.id)
                })

                # Revoke the token since balance changed
                OfflineTokenService.revoke_token(
                    db=db,
                    token_id=tx.offline_token_id,
                    revoked_by="SYSTEM",
                    reason=f"Used in offline transaction {tx.id}"
                )

                db.commit()

            except Exception as e:
                tx.sync_status = "REJECTED"
                tx.rejection_reason = f"Processing error: {str(e)}"
                processed["failed"] += 1
                processed["details"].append({
                    "tx_id": str(tx.id),
                    "status": "FAILED",
                    "reason": str(e)
                })
                db.commit()

        return processed

    @staticmethod
    def get_device_queue_status(
        db: Session,
        device_id: str
    ) -> Dict[str, Any]:
        """
        Get sync queue status for a device.

        Args:
            db: Database session
            device_id: Device ID

        Returns:
            Dictionary with queue status
        """
        pending = db.query(OfflineTransaction).filter(
            OfflineTransaction.device_id == device_id,
            OfflineTransaction.sync_status == "PENDING"
        ).count()

        synced = db.query(OfflineTransaction).filter(
            OfflineTransaction.device_id == device_id,
            OfflineTransaction.sync_status == "SYNCED"
        ).count()

        rejected = db.query(OfflineTransaction).filter(
            OfflineTransaction.device_id == device_id,
            OfflineTransaction.sync_status == "REJECTED"
        ).count()

        # Get active tokens for this device
        active_tokens = db.query(OfflineToken).filter(
            OfflineToken.device_id == device_id,
            OfflineToken.is_revoked == 0,
            OfflineToken.expires_at > datetime.utcnow()
        ).all()

        return {
            "device_id": device_id,
            "queue": {
                "pending": pending,
                "synced": synced,
                "rejected": rejected,
                "total": pending + synced + rejected
            },
            "active_tokens": len(active_tokens),
            "tokens": [t.to_dict() for t in active_tokens]
        }