"""Company management service"""
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.company import Company, CompanyPlan, CompanyStatus
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    """Service for company management operations"""

    @staticmethod
    def create_company(
        db: Session,
        company_data: CompanyCreate,
        created_by_user_id: str
    ) -> Company:
        """
        Create a new company.

        Args:
            db: Database session
            company_data: Company creation data
            created_by_user_id: ID of user creating the company

        Returns:
            Created company
        """
        # Check if slug already exists
        existing = db.query(Company).filter(
            Company.slug == company_data.slug
        ).first()

        if existing:
            raise ValueError(f"Company with slug '{company_data.slug}' already exists")

        # Get plan limits
        plan_limits = CompanyService.get_plan_limits(company_data.plan)

        # Create company
        company = Company(
            name=company_data.name,
            slug=company_data.slug,
            email=company_data.email,
            phone=company_data.phone,
            address=company_data.address,
            city=company_data.city,
            country=company_data.country,
            business_type=company_data.business_type,
            tax_id=company_data.tax_id,
            plan=company_data.plan or CompanyPlan.STARTER,
            max_venues=plan_limits["max_venues"],
            max_users=plan_limits["max_users"],
            status=CompanyStatus.ACTIVE,
            created_by=created_by_user_id
        )

        db.add(company)
        db.commit()
        db.refresh(company)

        return company

    @staticmethod
    def get_company_by_id(db: Session, company_id: str) -> Optional[Company]:
        """
        Get company by ID.

        Args:
            db: Database session
            company_id: Company ID

        Returns:
            Company or None
        """
        return db.query(Company).filter(
            Company.id == uuid.UUID(company_id)
        ).first()

    @staticmethod
    def get_company_by_slug(db: Session, slug: str) -> Optional[Company]:
        """
        Get company by slug.

        Args:
            db: Database session
            slug: Company slug

        Returns:
            Company or None
        """
        return db.query(Company).filter(
            Company.slug == slug
        ).first()

    @staticmethod
    def list_companies(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[CompanyStatus] = None
    ) -> List[Company]:
        """
        List companies with optional filters.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)

        Returns:
            List of companies
        """
        query = db.query(Company)

        if status:
            query = query.filter(Company.status == status)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_company(
        db: Session,
        company_id: str,
        company_update: CompanyUpdate
    ) -> Optional[Company]:
        """
        Update company information.

        Args:
            db: Database session
            company_id: Company ID
            company_update: Update data

        Returns:
            Updated company or None
        """
        company = CompanyService.get_company_by_id(db, company_id)

        if not company:
            return None

        # Update fields
        update_data = company_update.model_dump(exclude_unset=True)

        # Handle plan changes
        if "plan" in update_data:
            plan_limits = CompanyService.get_plan_limits(update_data["plan"])
            company.max_venues = plan_limits["max_venues"]
            company.max_users = plan_limits["max_users"]

        for field, value in update_data.items():
            setattr(company, field, value)

        company.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(company)

        return company

    @staticmethod
    def delete_company(db: Session, company_id: str, deleted_by: str) -> bool:
        """
        Soft delete a company.

        Args:
            db: Database session
            company_id: Company ID
            deleted_by: ID of user deleting the company

        Returns:
            True if deleted, False if not found
        """
        company = CompanyService.get_company_by_id(db, company_id)

        if not company:
            return False

        # Soft delete
        company.status = CompanyStatus.DELETED
        company.deleted_at = datetime.utcnow()
        company.deleted_by = deleted_by

        db.commit()

        return True

    @staticmethod
    def get_plan_limits(plan: CompanyPlan) -> dict:
        """
        Get limits for a given plan.

        Args:
            plan: Company plan

        Returns:
            Dictionary with plan limits
        """
        plan_limits = {
            CompanyPlan.STARTER: {
                "max_users": 10,
                "max_venues": 1,
                "max_cards": 1000,
                "max_transactions_month": 10000,
                "support_level": "email"
            },
            CompanyPlan.PRO: {
                "max_users": 50,
                "max_venues": 5,
                "max_cards": 5000,
                "max_transactions_month": 50000,
                "support_level": "priority"
            },
            CompanyPlan.ENTERPRISE: {
                "max_users": None,  # Unlimited
                "max_venues": None,  # Unlimited
                "max_cards": None,  # Unlimited
                "max_transactions_month": None,  # Unlimited
                "support_level": "dedicated"
            }
        }

        return plan_limits.get(plan, plan_limits[CompanyPlan.STARTER])

    @staticmethod
    def check_plan_limit(
        db: Session,
        company_id: str,
        limit_type: str,
        current_count: int
    ) -> bool:
        """
        Check if company has exceeded their plan limit.

        Args:
            db: Database session
            company_id: Company ID
            limit_type: Type of limit (users, venues, cards)
            current_count: Current usage count

        Returns:
            True if under limit, False if exceeded
        """
        company = CompanyService.get_company_by_id(db, company_id)

        if not company:
            return False

        limits = CompanyService.get_plan_limits(company.plan)

        # Enterprise has no limits
        max_limit = limits.get(f"max_{limit_type}")

        if max_limit is None:
            return True  # Unlimited

        return current_count < max_limit

    @staticmethod
    def get_company_stats(db: Session, company_id: str) -> dict:
        """
        Get company statistics.

        Args:
            db: Database session
            company_id: Company ID

        Returns:
            Dictionary with company stats
        """
        from app.models.card import Card
        from app.models.transaction import Transaction
        from app.models.user import User
        from datetime import timedelta

        company = CompanyService.get_company_by_id(db, company_id)

        if not company:
            return {}

        # Get current counts
        total_users = db.query(User).filter(User.company_id == uuid.UUID(company_id)).count()
        total_cards = db.query(Card).filter(Card.company_id == uuid.UUID(company_id)).count()

        # Get total balance
        cards = db.query(Card).filter(Card.company_id == uuid.UUID(company_id)).all()
        total_balance = sum(float(card.balance) for card in cards)

        # Get transaction volume (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        transactions = db.query(Transaction).filter(
            Transaction.company_id == uuid.UUID(company_id),
            Transaction.created_at >= thirty_days_ago
        ).all()

        total_transactions_30d = len(transactions)
        total_volume_30d = sum(float(t.amount) for t in transactions)

        # Get plan limits
        limits = CompanyService.get_plan_limits(company.plan)
        max_users = limits["max_users"]

        return {
            "company_id": str(company.id),
            "company_name": company.name,
            "total_users": total_users,
            "total_cards": total_cards,
            "total_balance": total_balance,
            "total_transactions_30d": total_transactions_30d,
            "total_volume_30d": total_volume_30d,
            "plan": str(company.plan),
            "max_users": max_users,
            "usage_percentage": (total_users / max_users * 100) if max_users else 0,
            "status": str(company.status),
            "created_at": company.created_at
        }