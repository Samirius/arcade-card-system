"""Dashboard and analytics API routes"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import get_db
from app.models import Card, Transaction, Machine, Location, User
from app.schemas.business import (
    DashboardStatsResponse, DashboardCardsResponse,
    DashboardRevenueResponse
)
from app.api.authorization import require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get comprehensive dashboard statistics.

    **Permissions:** SUPERVISOR and above

    Returns revenue, cards, transactions, and machine statistics.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Revenue stats
    revenue_today = Decimal(0.00)
    revenue_week = Decimal(0.00)
    revenue_month = Decimal(0.00)
    revenue_total = Decimal(0.00)

    all_transactions = db.query(Transaction).all()
    for t in all_transactions:
        if t.transaction_type == "ADD":
            revenue_total += t.amount
            if t.created_at >= today_start:
                revenue_today += t.amount
            if t.created_at >= week_start:
                revenue_week += t.amount
            if t.created_at >= month_start:
                revenue_month += t.amount

    # Card stats
    cards_total = db.query(Card).count()
    cards_active = db.query(Card).filter(Card.status == "ACTIVE").count()
    cards_inactive = cards_total - cards_active

    # Transaction stats
    transactions_today = db.query(Transaction).filter(
        Transaction.created_at >= today_start
    ).count()
    transactions_week = db.query(Transaction).filter(
        Transaction.created_at >= week_start
    ).count()
    transactions_month = db.query(Transaction).filter(
        Transaction.created_at >= month_start
    ).count()

    # Machine stats
    machines_total = db.query(Machine).count()
    machines_online = db.query(Machine).filter(Machine.status == "ONLINE").count()
    machines_offline = machines_total - machines_online

    # Customer stats
    # TODO: Count from customers table when implemented
    customers_total = 0

    return DashboardStatsResponse(
        revenue_today=revenue_today,
        revenue_week=revenue_week,
        revenue_month=revenue_month,
        revenue_total=revenue_total,
        cards_active=cards_active,
        cards_inactive=cards_inactive,
        cards_total=cards_total,
        transactions_today=transactions_today,
        transactions_week=transactions_week,
        transactions_month=transactions_month,
        machines_online=machines_online,
        machines_offline=machines_offline,
        machines_total=machines_total,
        customers_total=customers_total
    )


@router.get("/cards")
async def get_dashboard_cards(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get recent cards for dashboard.

    **Permissions:** SUPERVISOR and above

    Returns most recently created cards.
    """
    cards = db.query(Card).order_by(Card.created_at.desc()).limit(limit).all()

    total = db.query(Card).count()
    active = db.query(Card).filter(Card.status == "ACTIVE").count()
    inactive = total - active

    return {
        "cards": [
            {
                "id": c.id,
                "card_uid": c.card_uid,
                "owner": c.owner,
                "balance": c.balance,
                "card_type": c.card_type.value,
                "status": c.status.value,
                "created_at": c.created_at
            }
            for c in cards
        ],
        "total": total,
        "active": active,
        "inactive": inactive
    }


@router.get("/revenue")
async def get_dashboard_revenue(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get revenue breakdown for dashboard.

    **Permissions:** SUPERVISOR and above

    Returns revenue by day, machine, and location.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Revenue by day
    daily_revenue = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        day_revenue = db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_type == "ADD",
            Transaction.created_at >= day_start,
            Transaction.created_at < day_end
        ).scalar() or Decimal(0.00)

        daily_revenue.append({
            "date": day_start.date(),
            "revenue": day_revenue
        })

    # Revenue by machine (top 10)
    # TODO: Implement when machine_transaction table is added

    # Revenue by location (top 10)
    # TODO: Implement when location_transaction table is added

    # Top cards by total added
    top_cards = db.query(
        Transaction.card_uid,
        func.sum(Transaction.amount).label('total_added')
    ).filter(
        Transaction.transaction_type == "ADD",
        Transaction.created_at >= start_date
    ).group_by(Transaction.card_uid).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(10).all()

    top_cards_list = [
        {
            "card_uid": card[0],
            "total_added": card[1]
        }
        for card in top_cards
    ]

    return {
        "by_day": daily_revenue,
        "by_machine": [],
        "by_location": [],
        "top_cards": top_cards_list
    }


@router.get("/transactions/recent")
async def get_recent_transactions(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STAFF", "SUPERVISOR", "REGIONAL_MGR", "OPERATIONS", "ADMIN", "OWNER"]))
):
    """
    Get recent transactions for dashboard.

    **Permissions:** STAFF and above

    Returns most recent transactions.
    """
    transactions = db.query(Transaction).order_by(
        Transaction.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": t.id,
            "card_uid": t.card_uid,
            "amount": t.amount,
            "transaction_type": t.transaction_type,
            "payment_method": t.payment_method,
            "created_at": t.created_at,
            "notes": t.notes
        }
        for t in transactions
    ]