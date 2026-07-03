"""Admin-only user management API routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
import uuid

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.utils.password import hash_password
from app.api.authorization import require_role

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateAdmin(BaseModel):
    """Schema for admin-created user"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    role: str
    company_id: Optional[uuid.UUID] = None


class UserSafeResponse(BaseModel):
    """Safe user fields returned to clients (never includes password_hash)"""
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    status: str
    company_id: Optional[uuid.UUID]

    class Config:
        from_attributes = True


def _to_safe_response(user: User) -> UserSafeResponse:
    """Convert a User model instance to the safe response schema"""
    return UserSafeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        company_id=user.company_id,
    )


@router.post("/", response_model=UserSafeResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OWNER"]))
):
    """
    Create a new user (admin-managed).

    **Permissions:** ADMIN and OWNER only

    Creates the user as ACTIVE and verified, with the password hashed.
    Defaults company_id to the creating admin's company_id when not provided.
    """
    # Validate role against UserRole
    try:
        role = UserRole(user_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}. Must be one of: {', '.join(r.value for r in UserRole)}"
        )

    # Reject duplicate email
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    # Default company_id to the creating admin's company_id when not provided
    company_id = user_data.company_id if user_data.company_id is not None else getattr(current_user, "company_id", None)

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        role=role,
        status=UserStatus.ACTIVE,
        is_verified=True,
        company_id=company_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return _to_safe_response(new_user)


@router.get("/", response_model=List[UserSafeResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OWNER"]))
):
    """
    List all users.

    **Permissions:** ADMIN and OWNER only

    Returns safe fields only (never password_hash).
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [_to_safe_response(user) for user in users]
