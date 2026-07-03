"""Authorization dependencies"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.models.user import User, UserRole
from app.api.auth import get_current_user

security = HTTPBearer(auto_error=False)


def require_role(allowed_roles: list[str]):
    """
    Dependency factory for role-based authorization.

    Args:
        allowed_roles: List of role names allowed to access the endpoint

    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if current user has required role"""
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )

        return current_user

    return role_checker


def require_min_role(min_role: UserRole):
    """
    Dependency for hierarchical role authorization.

    Roles are hierarchical: CUSTOMER < STAFF < SUPERVISOR < REGIONAL_MGR < OPERATIONS < ADMIN < OWNER

    Args:
        min_role: Minimum role required to access the endpoint

    Returns:
        FastAPI dependency function
    """
    role_hierarchy = {
        UserRole.CUSTOMER: 0,
        UserRole.STAFF: 1,
        UserRole.SUPERVISOR: 2,
        UserRole.REGIONAL_MGR: 3,
        UserRole.OPERATIONS: 4,
        UserRole.ADMIN: 5,
        UserRole.OWNER: 6
    }

    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if current user has sufficient role"""
        user_role = current_user.role

        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(min_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required minimum role: {min_role.value}"
            )

        return current_user

    return role_checker


def require_any_role(*allowed_roles: UserRole):
    """
    Dependency for checking if user has ANY of the specified roles.

    Args:
        *allowed_roles: List of roles that grant access

    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Check if current user has any of the required roles"""
        user_role = current_user.role

        if user_role not in allowed_roles:
            role_names = [role.value for role in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(role_names)}"
            )

        return current_user

    return role_checker