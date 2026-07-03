"""Offline token API endpoints for device-side play management"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.schemas.offline import (
    OfflineTokenIssueRequest,
    OfflineTokenResponse,
    OfflineTokenValidationResponse,
    OfflineTransactionQueueRequest,
    OfflineSyncResult,
    DeviceQueueStatusResponse
)
from app.services.offline import OfflineTokenService
from app.api.auth import get_current_user
from app.api.authorization import require_role

router = APIRouter(prefix="/offline", tags=["offline"])


@router.post("/token/issue", response_model=OfflineTokenResponse)
async def issue_offline_token(
    request: OfflineTokenIssueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Issue a signed offline token for a card.

    **Permissions:** STAFF and above

    Tokens are short-lived (1-4 hours) and allow devices
    to operate without internet connectivity.
    """
    try:
        result = OfflineTokenService.issue_token(
            db=db,
            card_uid=request.card_uid,
            device_id=request.device_id,
            ttl_hours=request.ttl_hours
        )

        return OfflineTokenResponse(
            success=True,
            token=result["token"],
            token_id=result["token_id"],
            card_uid=result["card_uid"],
            balance=result["balance"],
            expires_at=result["expires_at"],
            device_id=result["device_id"],
            ttl_hours=result["ttl_hours"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/token/validate", response_model=OfflineTokenValidationResponse)
async def validate_offline_token(
    signed_token: str,
    db: Session = Depends(get_db)
):
    """
    Validate an offline token (public endpoint).

    This endpoint is used by devices to validate tokens
    before allowing offline play.
    """
    result = OfflineTokenService.validate_token(
        db=db,
        signed_token=signed_token
    )

    return OfflineTokenValidationResponse(**result)


@router.post("/token/revoke")
async def revoke_offline_token(
    token_id: str,
    reason: str,
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Revoke an offline token.

    **Permissions:** ADMIN and OWNER only

    Invalidates token immediately.
    """
    success = OfflineTokenService.revoke_token(
        db=db,
        token_id=token_id,
        revoked_by=str(current_user.id),
        reason=reason
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    return {
        "success": True,
        "message": "Token revoked successfully",
        "token_id": token_id
    }


@router.post("/token/revoke-all/{card_uid}")
async def revoke_all_card_tokens(
    card_uid: str,
    reason: str,
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Revoke all offline tokens for a card.

    **Permissions:** ADMIN and OWNER only

    Called automatically when balance changes.
    """
    count = OfflineTokenService.revoke_all_card_tokens(
        db=db,
        card_uid=card_uid,
        revoked_by=str(current_user.id),
        reason=reason
    )

    return {
        "success": True,
        "message": f"Revoked {count} tokens for card {card_uid}",
        "revoked_count": count
    }


@router.post("/transaction/queue")
async def queue_offline_transaction(
    transaction: OfflineTransactionQueueRequest,
    db: Session = Depends(get_db)
):
    """
    Queue an offline transaction for sync.

    This is a public endpoint used by devices
    when operating offline.
    """
    offline_tx = OfflineTokenService.queue_offline_transaction(
        db=db,
        card_uid=transaction.card_uid,
        amount=int(transaction.amount * 100),  # Convert to cents
        transaction_type=transaction.transaction_type,
        device_id=transaction.device_id,
        offline_token_id=transaction.offline_token_id,
        machine_id=transaction.machine_id,
        location_id=transaction.location_id,
        device_timestamp=transaction.device_timestamp,
        device_signature=transaction.device_signature
    )

    return {
        "success": True,
        "transaction_id": str(offline_tx.id),
        "status": "QUEUED",
        "message": "Transaction queued for sync"
    }


@router.post("/sync/process", response_model=OfflineSyncResult)
async def process_offline_sync(
    device_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Process pending offline transactions from sync queue.

    **Permissions:** ADMIN and OWNER only

    This endpoint is called when connectivity returns to
    process all queued offline transactions.
    """
    result = OfflineTokenService.process_sync_queue(
        db=db,
        device_id=device_id,
        limit=limit
    )

    return OfflineSyncResult(**result)


@router.get("/queue/status/{device_id}", response_model=DeviceQueueStatusResponse)
async def get_queue_status(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sync queue status for a device.

    **Permissions:** STAFF and above

    Returns pending/synced/rejected counts and active tokens.
    """
    status = OfflineTokenService.get_device_queue_status(
        db=db,
        device_id=device_id
    )

    return DeviceQueueStatusResponse(**status)


@router.get("/tokens/active")
async def list_active_tokens(
    card_uid: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List active offline tokens.

    **Permissions:** STAFF and above

    Filter by card_uid or device_id for specific views.
    """
    from app.models.offline import OfflineToken

    query = db.query(OfflineToken).filter(
        OfflineToken.is_revoked == 0,
        OfflineToken.expires_at > datetime.utcnow()
    )

    if card_uid:
        query = query.filter(OfflineToken.card_uid == card_uid)

    if device_id:
        query = query.filter(OfflineToken.device_id == device_id)

    tokens = query.order_by(OfflineToken.expires_at.desc()).limit(100).all()

    return {
        "total": len(tokens),
        "tokens": [t.to_dict() for t in tokens]
    }


@router.get("/transactions/pending")
async def list_pending_transactions(
    device_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List pending offline transactions awaiting sync.

    **Permissions:** STAFF and above
    """
    from app.models.offline import OfflineTransaction

    query = db.query(OfflineTransaction).filter(
        OfflineTransaction.sync_status == "PENDING"
    )

    if device_id:
        query = query.filter(OfflineTransaction.device_id == device_id)

    transactions = query.order_by(
        OfflineTransaction.created_at.asc()
    ).limit(limit).all()

    return {
        "total": len(transactions),
        "transactions": [t.to_dict() for t in transactions]
    }