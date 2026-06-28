"""Card management API routes"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models import Card, CardType, CardStatus, Transaction, User
from app.models.user import UserRole
from app.schemas.business import (
    CardCreate, CardUpdate, CardResponse, CardBalanceResponse,
    CardListFilter, BalanceAddResponse, BalanceChargeResponse, BalanceOperation
)
from app.utils.audit import log_action
from app.api.authorization import require_role
from app.api.auth import get_current_user
from app.utils.tenant import enforce_tenant_isolation

router = APIRouter(prefix="/cards", tags=["cards"])


def _check_card_tenant_access(db: Session, current_user: User, card: Card):
    """Verify that the current user can access this card (tenant isolation)."""
    if card is None:
        return
    # Only OWNER can access across all tenants
    if current_user.role == UserRole.OWNER:
        return
    user_company = getattr(current_user, 'company_id', None)
    card_company = getattr(card, 'company_id', None)
    # If card has no company, check if this user created it (via owner field matching email)
    if card_company is None:
        # Cards without company_id: only the creator (or OWNER) can access
        # We check if the card owner matches the user's email or full name
        user_name = f"{current_user.first_name} {current_user.last_name}"
        if card.owner in (current_user.email, user_name):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have access to this card"
        )
    # Card has company_id — user must match it
    if user_company is None or user_company != card_company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: card belongs to another company"
        )


@router.post("/", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    card_data: CardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Create a new card.

    **Permissions:** STAFF and above

    Creates a new arcade card with optional initial balance.
    Can link to an existing customer profile.
    """
    # Check if card UID already exists
    existing_card = db.query(Card).filter(Card.card_uid == card_data.card_uid).first()
    if existing_card:
        log_action(
            db=db,
            user_id=current_user.id,
            action="CARD_CREATE_FAILED",
            details=f"Card UID {card_data.card_uid} already exists"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card with this UID already exists"
        )

    # Create card
    new_card = Card(
        card_uid=card_data.card_uid,
        owner=card_data.owner,
        card_type=CardType[card_data.card_type],
        balance=card_data.initial_balance,
        status=CardStatus.ACTIVE,
        notes=card_data.notes,
        company_id=getattr(current_user, 'company_id', None)  # Auto-assign to user's company
    )

    db.add(new_card)

    # Create initial balance transaction if balance > 0
    if card_data.initial_balance > 0:
        initial_transaction = Transaction(
            card_uid=card_data.card_uid,
            amount=card_data.initial_balance,
            transaction_type="ADD",
            payment_method="CASH",
            user_id=current_user.id,
            notes="Initial balance"
        )
        db.add(initial_transaction)
        new_card.last_transaction_at = initial_transaction.created_at

    db.commit()
    db.refresh(new_card)

    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action="CARD_CREATE",
        details=f"Created card {card_data.card_uid} with initial balance {card_data.initial_balance}"
    )

    return new_card


@router.get("/", response_model=List[CardResponse])
async def list_cards(
    status: Optional[str] = None,
    card_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    List all cards with optional filters.

    **Permissions:** STAFF and above

    Can filter by status, card type, and search by card UID or owner.
    """
    query = db.query(Card)

    # Enforce tenant isolation (super-admins see all)
    query = enforce_tenant_isolation(db, str(current_user.id), query, Card)

    # Apply filters
    if status:
        try:
            query = query.filter(Card.status == CardStatus[status])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if card_type:
        try:
            query = query.filter(Card.card_type == CardType[card_type])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid card type: {card_type}")

    if search:
        query = query.filter(
            (Card.card_uid.ilike(f"%{search}%")) |
            (Card.owner.ilike(f"%{search}%"))
        )

    # Order by created_at desc
    query = query.order_by(Card.created_at.desc())

    # Apply pagination
    cards = query.offset(offset).limit(limit).all()

    return cards


@router.get("/stats/summary")
async def get_cards_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get cards summary statistics.

    **Permissions:** SUPERVISOR and above
    """
    # Base query with tenant isolation
    base_query = db.query(Card)
    base_query = enforce_tenant_isolation(db, str(current_user.id), base_query, Card)

    total_cards = base_query.count()
    active_cards = base_query.filter(Card.status == CardStatus.ACTIVE).count()
    inactive_cards = total_cards - active_cards

    # Count by card type
    card_type_counts = {}
    for card_type in CardType:
        count = base_query.filter(Card.card_type == card_type).count()
        card_type_counts[card_type.value] = count

    # Total balance across all cards
    total_balance = base_query.with_entities(Card.balance).all()
    total_balance_sum = sum([balance[0] for balance in total_balance]) if total_balance else Decimal(0.00)

    return {
        "total_cards": total_cards,
        "active_cards": active_cards,
        "inactive_cards": inactive_cards,
        "card_type_counts": card_type_counts,
        "total_balance": total_balance_sum
    }


@router.get("/me", response_model=CardResponse)
async def get_my_card(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current user's card (customer portal).
    Matches card by owner field = user's email or full name.
    """
    card = (
        db.query(Card)
        .filter(Card.owner.in_([current_user.email, getattr(current_user, 'full_name', '')]))
        .filter(Card.status == CardStatus.ACTIVE)
        .first()
    )
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active card found for your account"
        )
    return card


@router.get("/me/transactions", response_model=List[dict])
async def get_my_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get transactions for the current user's card (customer portal).
    """
    card = (
        db.query(Card)
        .filter(Card.owner.in_([current_user.email, getattr(current_user, 'full_name', '')]))
        .filter(Card.status == CardStatus.ACTIVE)
        .first()
    )
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active card found for your account"
        )
    transactions = (
        db.query(Transaction)
        .filter(Transaction.card_uid == card.card_uid)
        .order_by(Transaction.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(t.id),
            "card_uid": t.card_uid,
            "amount": float(t.amount),
            "transaction_type": t.transaction_type,
            "type": t.transaction_type,
            "payment_method": t.payment_method,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in transactions
    ]


@router.get("/{card_uid}", response_model=CardResponse)
async def get_card(
    card_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get card details by UID.

    **Permissions:** STAFF and above
    """
    card = db.query(Card).filter(Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    _check_card_tenant_access(db, current_user, card)

    return card


@router.get("/{card_uid}/balance", response_model=CardBalanceResponse)
async def get_card_balance(
    card_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get card balance and status.

    **Permissions:** STAFF and above

    This is a fast endpoint for kiosk/card readers to check balance.
    """
    card = db.query(Card).filter(Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    _check_card_tenant_access(db, current_user, card)

    return {
        "card_uid": card.card_uid,
        "balance": card.balance,
        "status": card.status.value,
        "card_type": card.card_type.value,
        "owner": card.owner
    }


@router.put("/{card_uid}", response_model=CardResponse)
async def update_card(
    card_uid: str,
    card_data: CardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Update card details.

    **Permissions:** SUPERVISOR and above

    Can update owner name, card type, status, and notes.
    """
    card = db.query(Card).filter(Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    _check_card_tenant_access(db, current_user, card)

    # Update fields
    if card_data.owner is not None:
        card.owner = card_data.owner
    if card_data.card_type is not None:
        card.card_type = CardType[card_data.card_type]
    if card_data.status is not None:
        card.status = CardStatus[card_data.status]
    if card_data.notes is not None:
        card.notes = card_data.notes

    db.commit()
    db.refresh(card)

    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action="CARD_UPDATE",
        details=f"Updated card {card_uid}"
    )

    return card


@router.post("/{card_uid}/activate", response_model=CardResponse)
async def activate_card(
    card_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Activate a card.

    **Permissions:** SUPERVISOR and above

    Changes card status to ACTIVE.
    """
    card = db.query(Card).filter(Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    _check_card_tenant_access(db, current_user, card)

    if card.status == CardStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Card is already active")

    card.status = CardStatus.ACTIVE
    db.commit()
    db.refresh(card)

    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action="CARD_ACTIVATE",
        details=f"Activated card {card_uid}"
    )

    return card


@router.post("/{card_uid}/deactivate", response_model=CardResponse)
async def deactivate_card(
    card_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Deactivate a card.

    **Permissions:** SUPERVISOR and above

    Changes card status to INACTIVE. Card cannot be used until reactivated.
    """
    card = db.query(Card).filter(Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    _check_card_tenant_access(db, current_user, card)

    if card.status == CardStatus.INACTIVE:
        raise HTTPException(status_code=400, detail="Card is already inactive")

    card.status = CardStatus.INACTIVE
    db.commit()
    db.refresh(card)

    # Log action
    log_action(
        db=db,
        user_id=current_user.id,
        action="CARD_DEACTIVATE",
        details=f"Deactivated card {card_uid}"
    )

    return card


@router.post("/{card_uid}/add-credit", response_model=BalanceAddResponse)
async def add_card_credit(
    card_uid: str,
    operation: BalanceOperation,
    payment_method: str = Query("CASH", description="Payment method: CASH, CARD, TRANSFER"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Add credit to a card.

    **Permissions:** STAFF and above

    Staff can add credit for cash payments.
    Supervisors+ can also refund or adjust.
    Uses BalanceLedgerService for atomic operation + audit trail.
    """
    from app.services.ledger import BalanceLedgerService

    try:
        result = BalanceLedgerService.add_balance(
            db=db,
            card_uid=card_uid,
            amount=operation.amount,
            user_id=str(current_user.id),
            notes=operation.notes or f"Added {operation.amount} credits via {payment_method}",
            metadata={"payment_method": payment_method, "endpoint": "add-credit"}
        )

        return {
            "success": True,
            "message": f"Successfully added {operation.amount} credits to card",
            "card_uid": card_uid,
            "old_balance": result["balance_before"],
            "new_balance": result["balance_after"],
            "transaction_id": None
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Card not found")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{card_uid}/charge", response_model=BalanceChargeResponse)
async def charge_card(
    card_uid: str,
    operation: BalanceOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Charge a card (deduct credits).

    **Permissions:** STAFF and above

    Used when a customer plays a game or uses a service.
    Uses BalanceLedgerService for atomic operation + audit trail.
    """
    from app.services.ledger import BalanceLedgerService

    try:
        result = BalanceLedgerService.deduct_balance(
            db=db,
            card_uid=card_uid,
            amount=operation.amount,
            user_id=str(current_user.id),
            notes=operation.notes or f"Charged {operation.amount} credits",
            metadata={"endpoint": "charge"}
        )

        return {
            "success": True,
            "message": f"Successfully charged {operation.amount} credits from card",
            "card_uid": card_uid,
            "old_balance": result["balance_before"],
            "new_balance": result["balance_after"],
            "amount_charged": operation.amount,
            "transaction_id": None
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Card not found")
        if "insufficient" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{card_uid}/transactions", response_model=List[dict])
async def get_card_transactions(
    card_uid: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get transaction history for a specific card.

    **Permissions:** STAFF and above
    """
    card = db.query(Card).filter(Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    _check_card_tenant_access(db, current_user, card)

    transactions = db.query(Transaction).filter(
        Transaction.card_uid == card_uid
    ).order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": t.id,
            "amount": t.amount,
            "transaction_type": t.transaction_type,
            "payment_method": t.payment_method,
            "created_at": t.created_at,
            "notes": t.notes
        }
        for t in transactions
    ]