"""Multi-tenancy utilities for tenant isolation"""
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from app.models import User, Card, Transaction


def get_user_company_id(user) -> Optional[uuid.UUID]:
    """
    Get the company ID for a user.
    
    Args:
        user: User object
        
    Returns:
        Company ID or None for super-admins
    """
    return getattr(user, 'company_id', None)


def get_current_company_id(db: Session, user_id: str) -> Optional[uuid.UUID]:
    """
    Get current user's company ID from database.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Company ID or None for super-admins
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return get_user_company_id(user)


def enforce_tenant_isolation(db: Session, user_id: str, query, model):
    """
    Enforce tenant isolation on a query.
    
    This adds a WHERE clause to filter by company_id.
    Super-admins (company_id=NULL) can access all data.
    
    Args:
        db: Database session
        user_id: User ID
        query: SQLAlchemy query object
        model: Model class (User, Card, Transaction, etc.)
        
    Returns:
        Query with tenant filter applied
    """
    company_id = get_current_company_id(db, user_id)
    
    # Super-admins (NULL company_id) can see all data
    if company_id is None:
        return query
    
    # Add tenant filter to query
    if hasattr(model, 'company_id'):
        return query.filter(model.company_id == company_id)
    
    # Model doesn't support multi-tenancy yet
    return query


def require_same_tenant(db: Session, current_user_id: str, target_company_id: uuid.UUID) -> bool:
    """
    Check if user belongs to the same tenant as target resource.
    
    Args:
        db: Database session
        current_user_id: User ID
        target_company_id: Company ID to check
        
    Returns:
        True if same tenant or user is super-admin, False otherwise
    """
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        return False
    
    user_company_id = get_user_company_id(user)
    
    # Super-admins can access any tenant
    if user_company_id is None:
        return True
    
    return user_company_id == target_company_id


def get_accessible_companies(db: Session, user_id: str) -> List[uuid.UUID]:
    """
    Get list of company IDs a user can access.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        List of company IDs user can access (empty list = super-admin)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    company_id = get_user_company_id(user)
    
    # Super-admins can access all companies
    if company_id is None:
        # Return all company IDs from companies table
        from app.models import Company
        companies = db.query(Company).all()
        return [c.id for c in companies]
    
    return [company_id]


def create_isolation_middleware():
    """
    Create middleware function for tenant isolation.
    
    This dependency function checks if a user can access
    a resource by checking company_id.
    
    Returns:
        FastAPI dependency function
    """
    from fastapi import HTTPException, status
    from app.api.auth import get_current_user
    
    async def check_tenant_isolation(
        current_user: User = Depends(get_current_user),
        resource_company_id: uuid.UUID = None,
        db: Session = Depends(get_db)
    ):
        """
        Check if user can access a resource by company.
        
        Args:
            current_user: Current authenticated user
            resource_company_id: Company ID of the resource being accessed
            db: Database session
            
        Raises:
            HTTPException 403 if user cannot access this resource
        """
        # Super-admins can access everything
        if resource_company_id is None:
            return
        
        user_company_id = get_user_company_id(current_user)
        
        if user_company_id is None:
            return  # Super-admin can access all
        
        if user_company_id != resource_company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot access resources from another company"
            )
    
    return check_tenant_isolation