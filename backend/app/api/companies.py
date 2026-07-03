"""Company management endpoints for multi-tenant system"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.models.company import Company, CompanyPlan, CompanyStatus
from app.models.user import User, UserRole
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyStats
from app.api.auth import get_current_user
from app.api.authorization import require_role

router = APIRouter(prefix="/companies", tags=["companies"])


def require_company_admin():
    """Dependency to ensure user is a company admin (OWNER, ADMIN, or REGIONAL_MGR)"""
    async def check_company_admin(current_user: User = Depends(get_current_user)):
        if not current_user.has_role(UserRole.OWNER, UserRole.ADMIN, UserRole.REGIONAL_MGR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage companies"
            )
        return current_user
    return check_company_admin


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(require_role([UserRole.OWNER])),
    db: Session = Depends(get_db)
):
    """
    Create a new company/tenant.

    **Permissions:** OWNER only

    Used to create a new customer/company in the system.
    """
    # Check if company slug already exists
    existing = db.query(Company).filter(Company.slug == company_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company slug already exists"
        )

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
        status=CompanyStatus.ACTIVE,
        created_by=str(current_user.id)
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    # Log company creation
    from app.utils.audit import log_audit
    log_audit(
        db=db,
        action="CREATE",
        resource_type="company",
        resource_id=str(company.id),
        user_id=str(current_user.id),
        ip_address=None,
        new_values={
            "name": company.name,
            "slug": company.slug,
            "plan": str(company.plan)
        },
        success=True
    )

    return company


@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all companies.

    **Permissions:** OWNER can see all, others see only their company
    """
    from app.utils.tenant import get_user_company_id

    user_company_id = get_user_company_id(current_user)

    # Super-admins see all companies
    if user_company_id is None:
        companies = db.query(Company).offset(skip).limit(limit).all()
    else:
        # Regular users see only their company
        companies = db.query(Company).filter(
            Company.id == user_company_id
        ).offset(skip).limit(limit).all()

    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get company details by ID.

    **Permissions:** Users can only see their own company (unless super-admin)
    """
    from app.utils.tenant import require_same_tenant, get_user_company_id

    company = db.query(Company).filter(Company.id == uuid.UUID(company_id)).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check tenant isolation
    user_company_id = get_user_company_id(current_user)
    if user_company_id is not None:
        if not require_same_tenant(db, str(current_user.id), company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access this company"
            )

    return company


@router.get("/{company_id}/stats", response_model=CompanyStats)
async def get_company_stats(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get company statistics and usage metrics.

    **Permissions:** Company admin only
    """
    from app.utils.tenant import require_same_tenant, get_user_company_id

    company = db.query(Company).filter(Company.id == uuid.UUID(company_id)).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check tenant isolation
    user_company_id = get_user_company_id(current_user)
    if user_company_id is not None:
        if not require_same_tenant(db, str(current_user.id), company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access this company"
            )

    # Calculate stats
    from app.models.card import Card
    from app.models.transaction import Transaction
    from app.models.user import User

    total_users = db.query(User).filter(User.company_id == company.id).count()
    total_cards = db.query(Card).filter(Card.company_id == company.id).count()

    # Calculate total balance
    total_balance = db.query(Card).filter(
        Card.company_id == company.id
    ).all()
    total_balance_amount = sum(float(card.balance) for card in total_balance)

    # Calculate transaction volume (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    transactions = db.query(Transaction).filter(
        Transaction.company_id == company.id,
        Transaction.created_at >= thirty_days_ago
    ).all()

    total_transactions = len(transactions)
    total_volume = sum(float(t.amount) for t in transactions)

    # Calculate plan limits
    plan_limits = {
        "STARTER": {"max_users": 10, "max_venues": 1},
        "PRO": {"max_users": 50, "max_venues": 5},
        "ENTERPRISE": {"max_users": None, "max_venues": None}  # Unlimited
    }

    limits = plan_limits.get(str(company.plan), {"max_users": 10, "max_venues": 1})
    max_users = limits["max_users"]

    return CompanyStats(
        company_id=str(company.id),
        company_name=company.name,
        total_users=total_users,
        total_cards=total_cards,
        total_balance=total_balance_amount,
        total_transactions_30d=total_transactions,
        total_volume_30d=total_volume,
        plan=str(company.plan),
        max_users=max_users,
        usage_percentage=(total_users / max_users * 100) if max_users else 0,
        status=str(company.status),
        created_at=company.created_at
    )


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str,
    company_update: CompanyUpdate,
    current_user: User = Depends(require_company_admin()),
    db: Session = Depends(get_db)
):
    """
    Update company information.

    **Permissions:** Company admin only (OWNER, ADMIN, REGIONAL_MGR)
    """
    from app.utils.tenant import require_same_tenant, get_user_company_id

    company = db.query(Company).filter(Company.id == uuid.UUID(company_id)).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check tenant isolation
    user_company_id = get_user_company_id(current_user)
    if user_company_id is not None:
        if not require_same_tenant(db, str(current_user.id), company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access this company"
            )

    # Update fields
    update_data = company_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    company.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(company)

    # Log update
    from app.utils.audit import log_audit
    log_audit(
        db=db,
        action="UPDATE",
        resource_type="company",
        resource_id=str(company.id),
        user_id=str(current_user.id),
        ip_address=None,
        new_values=update_data,
        success=True
    )

    return company


@router.delete("/{company_id}")
async def delete_company(
    company_id: str,
    current_user: User = Depends(require_role([UserRole.OWNER])),
    db: Session = Depends(get_db)
):
    """
    Delete a company (soft delete).

    **Permissions:** OWNER only

    Sets status to DELETED but retains data for audit.
    """
    from app.utils.tenant import require_same_tenant, get_user_company_id

    company = db.query(Company).filter(Company.id == uuid.UUID(company_id)).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check tenant isolation
    user_company_id = get_user_company_id(current_user)
    if user_company_id is not None:
        if not require_same_tenant(db, str(current_user.id), company.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access this company"
            )

    # Soft delete
    company.status = CompanyStatus.DELETED
    company.deleted_at = datetime.utcnow()
    company.deleted_by = str(current_user.id)

    db.commit()

    # Log deletion
    from app.utils.audit import log_audit
    log_audit(
        db=db,
        action="DELETE",
        resource_type="company",
        resource_id=str(company.id),
        user_id=str(current_user.id),
        ip_address=None,
        new_values={"status": "DELETED"},
        success=True
    )

    return {"message": "Company deleted successfully", "company_id": company_id}