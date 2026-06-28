"""Transaction management API routes"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

from app.database import get_db
from app.models import Transaction, Card, User
from app.schemas.business import TransactionCreate, TransactionResponse, TransactionListFilter
from app.utils.audit import log_action
from app.api.authorization import require_role
from app.utils.tenant import enforce_tenant_isolation

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Create a new transaction.

    **Permissions:** STAFF and above

    Creates a transaction (ADD, DEDUCT, or REFUND) and updates card balance.
    """
    # Get card
    card = db.query(Card).filter(Card.card_uid == transaction_data.card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Check card status
    if not card.can_transact():
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transact on {card.status.value} card"
        )

    # Process transaction
    if transaction_data.transaction_type == "ADD":
        card.add_balance(transaction_data.amount)
    elif transaction_data.transaction_type == "DEDUCT":
        if card.balance < transaction_data.amount:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Card has {card.balance}, attempting to deduct {transaction_data.amount}"
            )
        card.deduct_balance(transaction_data.amount)
    elif transaction_data.transaction_type == "REFUND":
        card.add_balance(transaction_data.amount)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid transaction type")

    card.last_transaction_at = datetime.utcnow()

    # Create transaction record
    new_transaction = Transaction(
        card_uid=transaction_data.card_uid,
        amount=transaction_data.amount,
        transaction_type=transaction_data.transaction_type,
        payment_method=transaction_data.payment_method,
        user_id=current_user.id,
        notes=transaction_data.notes
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action="TRANSACTION_CREATE",
        details=f"{transaction_data.transaction_type} {transaction_data.amount} to/from card {transaction_data.card_uid}"
    )

    return new_transaction


@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    card_uid: Optional[str] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    List transactions with optional filters.

    **Permissions:** STAFF and above

    Can filter by card UID, transaction type, and date range.
    """
    query = db.query(Transaction)

    # Enforce tenant isolation via card company_id
    from app.models.card import Card
    user_company = getattr(current_user, 'company_id', None)
    if user_company is not None:
        # Filter transactions to only those for cards in the user's company
        company_card_uids = db.query(Card.card_uid).filter(
            Card.company_id == user_company
        ).subquery()
        query = query.filter(Transaction.card_uid.in_(company_card_uids))

    # Apply filters
    if card_uid:
        query = query.filter(Transaction.card_uid == card_uid)

    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    if start_date:
        query = query.filter(Transaction.created_at >= start_date)

    if end_date:
        query = query.filter(Transaction.created_at <= end_date)

    # Order by created_at desc
    query = query.order_by(Transaction.created_at.desc())

    # Apply pagination
    transactions = query.offset(offset).limit(limit).all()

    return transactions


@router.get("/stats/summary")
async def get_transactions_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get transaction summary statistics.

    **Permissions:** SUPERVISOR and above

    Returns total transactions, revenue, and breakdown by type.
    """
    query = db.query(Transaction)

    # Apply date filters
    if start_date:
        query = query.filter(Transaction.created_at >= start_date)
    if end_date:
        query = query.filter(Transaction.created_at <= end_date)

    transactions = query.all()

    # Calculate stats
    total_transactions = len(transactions)
    total_revenue = Decimal(0.00)
    add_transactions = 0
    deduct_transactions = 0
    refund_transactions = 0

    for t in transactions:
        if t.transaction_type == "ADD":
            total_revenue += t.amount
            add_transactions += 1
        elif t.transaction_type == "DEDUCT":
            deduct_transactions += 1
        elif t.transaction_type == "REFUND":
            total_revenue -= t.amount
            refund_transactions += 1

    return {
        "total_transactions": total_transactions,
        "total_revenue": total_revenue,
        "add_transactions": add_transactions,
        "deduct_transactions": deduct_transactions,
        "refund_transactions": refund_transactions,
        "period": {
            "start_date": start_date,
            "end_date": end_date
        }
    }


@router.get("/stats/daily")
async def get_daily_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get daily transaction statistics for the last N days.

    **Permissions:** SUPERVISOR and above

    Returns daily revenue and transaction counts.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    daily_stats = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        day_transactions = db.query(Transaction).filter(
            Transaction.created_at >= day_start,
            Transaction.created_at < day_end
        ).all()

        day_revenue = Decimal(0.00)
        day_add_count = 0
        day_deduct_count = 0

        for t in day_transactions:
            if t.transaction_type == "ADD":
                day_revenue += t.amount
                day_add_count += 1
            elif t.transaction_type == "DEDUCT":
                day_deduct_count += 1

        daily_stats.append({
            "date": day_start.date(),
            "revenue": day_revenue,
            "add_transactions": day_add_count,
            "deduct_transactions": day_deduct_count,
            "total_transactions": len(day_transactions)
        })

    return daily_stats


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get transaction details by ID.

    **Permissions:** STAFF and above
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction