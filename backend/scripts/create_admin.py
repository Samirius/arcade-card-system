#!/usr/bin/env python
"""
Standalone seed script to create (or update) an admin/owner user.

Reads configuration from environment variables:
    ADMIN_EMAIL    - required, email address for the admin/owner account
    ADMIN_PASSWORD - required, plain text password (will be hashed)
    ADMIN_ROLE     - optional, one of the UserRole values (default: "OWNER")

The account is created (or updated) as ACTIVE and verified, with the
password hashed via the app's standard password hashing utility.

Idempotent: if a user with ADMIN_EMAIL already exists, this script updates
that user's password, role, and status instead of raising an error.

Usage (from the backend/ directory):
    SECRET_KEY=... DATABASE_URL=... ENVIRONMENT=development \\
    ADMIN_EMAIL=owner@example.com ADMIN_PASSWORD='SomeStrongPass123!' \\
    PYTHONPATH=. /path/to/venv/bin/python scripts/create_admin.py
"""
import os
import sys

from app.database import SessionLocal
from app.models.user import User, UserRole, UserStatus
from app.utils.password import hash_password


def main() -> int:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_role_str = os.getenv("ADMIN_ROLE", "OWNER")

    if not admin_email:
        print("ERROR: ADMIN_EMAIL environment variable is required", file=sys.stderr)
        return 1

    if not admin_password:
        print("ERROR: ADMIN_PASSWORD environment variable is required", file=sys.stderr)
        return 1

    try:
        admin_role = UserRole(admin_role_str)
    except ValueError:
        valid_roles = ", ".join(role.value for role in UserRole)
        print(
            f"ERROR: Invalid ADMIN_ROLE '{admin_role_str}'. Must be one of: {valid_roles}",
            file=sys.stderr,
        )
        return 1

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == admin_email).first()

        if existing_user:
            existing_user.password_hash = hash_password(admin_password)
            existing_user.role = admin_role
            existing_user.status = UserStatus.ACTIVE
            existing_user.is_verified = True
            db.commit()
            print(
                f"SUCCESS: Updated existing user '{admin_email}' "
                f"(role={admin_role.value}, status=ACTIVE, verified=True)"
            )
        else:
            new_user = User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                first_name="Admin",
                last_name="User",
                role=admin_role,
                status=UserStatus.ACTIVE,
                is_verified=True,
            )
            db.add(new_user)
            db.commit()
            print(
                f"SUCCESS: Created new user '{admin_email}' "
                f"(role={admin_role.value}, status=ACTIVE, verified=True)"
            )

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
