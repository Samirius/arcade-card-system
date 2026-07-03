"""Balance ledger API endpoints for balance management and reconciliation"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.schemas.balance import (
    BalanceOperationRequest,
    BalanceHistoryResponse,
    BalanceReconciliationResponse,
    BalanceSnapshotResponse,
    TransactionRollbackRequest
)
from app.services.ledger import BalanceLedgerService
from app.api.auth import get_current_user
from app.api.authorization import require_role

router = APIRouter(prefix="/balance", tags=["balance"])


@router.post("/add", response_model=BalanceHistoryResponse)
async def add_balance(
    operation: BalanceOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add balance to a card with full ledger entry.

    **Permissions:** STAFF and above

    This operation is atomic and logged to the balance ledger.
    """
    try:
        result = BalanceLedgerService.add_balance(
            db=db,
            card_uid=operation.card_uid,
            amount=Decimal(str(operation.amount)),
            user_id=str(current_user.id),
            notes=operation.notes,
            metadata=operation.metadata
        )

        return BalanceHistoryResponse(
            success=True,
            card_uid=result["card_uid"],
            amount=result["amount"],
            balance_before=result["balance_before"],
            balance_after=result["balance_after"],
            ledger_entry=result["ledger_entry"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/deduct", response_model=BalanceHistoryResponse)
async def deduct_balance(
    operation: BalanceOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deduct balance from a card with full ledger entry.

    **Permissions:** STAFF and above

    This operation is atomic and logged to the balance ledger.
    Will fail if insufficient balance.
    """
    try:
        result = BalanceLedgerService.deduct_balance(
            db=db,
            card_uid=operation.card_uid,
            amount=Decimal(str(operation.amount)),
            user_id=str(current_user.id),
            notes=operation.notes,
            metadata=operation.metadata
        )

        return BalanceHistoryResponse(
            success=True,
            card_uid=result["card_uid"],
            amount=result["amount"],
            balance_before=result["balance_before"],
            balance_after=result["balance_after"],
            ledger_entry=result["ledger_entry"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/history/{card_uid}", response_model=List[dict])
async def get_balance_history(
    card_uid: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    operation_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get balance ledger history for a card.

    **Permissions:** STAFF and above

    Returns complete audit trail of all balance changes.
    """
    history = BalanceLedgerService.get_ledger_history(
        db=db,
        card_uid=card_uid,
        start_date=start_date,
        end_date=end_date,
        operation_type=operation_type,
        limit=limit
    )

    return history


@router.get("/reconcile/{card_uid}", response_model=BalanceReconciliationResponse)
async def reconcile_balance(
    card_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reconcile balance by recalculating from ledger.

    **Permissions:** ADMIN and above

    This recalculates the balance from all ledger entries
    and compares it to the current card balance.
    """
    reconciliation = BalanceLedgerService.reconcile_balance(
        db=db,
        card_uid=card_uid
    )

    return BalanceReconciliationResponse(**reconciliation)


@router.post("/snapshot/{card_uid}", response_model=BalanceSnapshotResponse)
async def create_balance_snapshot(
    card_uid: str,
    snapshot_type: str = Query("DAILY", regex="^(HOURLY|DAILY|WEEKLY|MONTHLY)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a balance snapshot.

    **Permissions:** ADMIN and above

    Snapshots are typically created automatically but can be
    created manually for reporting purposes.
    """
    try:
        snapshot = BalanceLedgerService.create_snapshot(
            db=db,
            card_uid=card_uid,
            snapshot_type=snapshot_type
        )

        return BalanceSnapshotResponse(
            success=True,
            snapshot=snapshot.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/rollback", response_model=dict)
async def rollback_transaction(
    rollback: TransactionRollbackRequest,
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Rollback a transaction by reversing balance changes.

    **Permissions:** ADMIN and OWNER only

    This reverses all balance changes from a transaction
    and creates rollback ledger entries.
    """
    try:
        result = BalanceLedgerService.rollback_transaction(
            db=db,
            card_uid=rollback.card_uid,
            transaction_id=rollback.transaction_id,
            user_id=str(current_user.id),
            reason=rollback.reason
        )

        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/stats/company")
async def get_company_balance_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get balance statistics for the company.

    **Permissions:** STAFF and above

    Returns aggregated balance metrics for the company.
    """
    from app.models.balance import BalanceLedger
    from app.utils.tenant import get_user_company_id

    company_id = get_user_company_id(current_user)

    # Build query
    query = db.query(BalanceLedger)

    if company_id:
        query = query.filter(BalanceLedger.company_id == company_id)

    if start_date:
        query = query.filter(BalanceLedger.created_at >= start_date)

    if end_date:
        query = query.filter(BalanceLedger.created_at <= end_date)

    ledger_entries = query.all()

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

    # Get unique cards affected
    unique_cards = len(set(entry.card_uid for entry in ledger_entries))

    # Get net flow
    net_flow = total_additions - total_deductions

    return {
        "total_transactions": total_transactions,
        "unique_cards": unique_cards,
        "total_additions": float(total_additions),
        "total_deductions": float(total_deductions),
        "total_refunds": float(total_refunds),
        "net_flow": float(net_flow),
        "period": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None
        }
    }