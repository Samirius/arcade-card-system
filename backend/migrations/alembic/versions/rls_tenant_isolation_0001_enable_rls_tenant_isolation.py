"""enable rls tenant isolation

Revision ID: rls_tenant_isolation_0001
Revises: 8a48c49360ec
Create Date: 2026-07-04 02:32:26.357527

BE-1: PostgreSQL Row-Level Security (RLS) for tenant isolation
==============================================================

Defense-in-depth so that even a compromised or buggy query path cannot read or
write another tenant's rows: the database itself enforces the ``company_id``
boundary.

Covered tables (every tenant DATA table that carries a ``company_id``):

    cards, transactions, balance_ledger, balance_snapshots,
    devices, offline_tokens, offline_transactions,
    charge_idempotency, house_accounts, locations

For each covered table this migration:
    * ``ENABLE ROW LEVEL SECURITY``
    * ``FORCE ROW LEVEL SECURITY`` (so even the table OWNER is subject to the
      policy — otherwise the owning role silently bypasses RLS)
    * creates a single FOR ALL policy whose USING and WITH CHECK expression is::

          current_setting('app.is_superadmin', true) = 'on'
          OR company_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid

Tenant context is supplied per request via two GUCs set with ``SET LOCAL`` in
the auth dependencies (see app/api/auth.py and app/api/devices.py):
    * ``app.tenant_id``     — the caller's company_id (empty string if NULL)
    * ``app.is_superadmin`` — 'on' for a super-admin (company_id IS NULL), else 'off'

``current_setting(..., true)`` uses ``missing_ok=true`` so an UNSET GUC returns
NULL instead of erroring. ``NULLIF(x, '')`` turns the empty-string sentinel back
into NULL so the ``::uuid`` cast never sees ''.  With neither GUC set the
predicate is ``NULL = ... `` → NULL → the row is filtered out, i.e. a connection
with no tenant context sees NO tenant rows (fail-closed).

IMPORTANT — this only takes effect for a NON-superuser, NOBYPASSRLS role.
PostgreSQL superusers and roles with BYPASSRLS ignore RLS entirely. Production
must point ``DATABASE_URL`` at the ``arcade_app`` role created by
``backend/migrations/setup_app_role.sql`` (LOGIN, NOSUPERUSER, NOBYPASSRLS).

This migration is additive. It does not touch ``users`` (login must resolve a
user by email *before* any tenant context exists — RLS there would break
authentication), nor the non-tenant bookkeeping tables ``alembic_version`` and
``refresh_token_blacklist``.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'rls_tenant_isolation_0001'
down_revision: Union[str, None] = '8a48c49360ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tenant DATA tables that have a ``company_id`` column and therefore get RLS.
# Confirmed against backend/app/models/*.py.
RLS_TABLES: tuple[str, ...] = (
    "cards",
    "transactions",
    "balance_ledger",
    "balance_snapshots",
    "devices",
    "offline_tokens",
    "offline_transactions",
    "charge_idempotency",
    "house_accounts",
    "locations",
)

# Policy name used on every covered table.
POLICY_NAME = "tenant_isolation"

# The tenant-scoping predicate, shared by USING and WITH CHECK.
#   * super-admin (app.is_superadmin = 'on') sees/writes everything
#   * otherwise a row is visible/writable only when its company_id matches the
#     app.tenant_id GUC
#   * missing_ok=true (the `true` 2nd arg) means an UNSET GUC yields NULL rather
#     than raising, and NULLIF(...,'') keeps the '' sentinel out of the ::uuid cast
POLICY_EXPRESSION = (
    "current_setting('app.is_superadmin', true) = 'on' "
    "OR company_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;')
        # Idempotent: drop any prior policy of the same name before (re)creating.
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";')
        op.execute(
            f'CREATE POLICY {POLICY_NAME} ON "{table}"\n'
            f"    FOR ALL\n"
            f"    USING ({POLICY_EXPRESSION})\n"
            f"    WITH CHECK ({POLICY_EXPRESSION});"
        )


def downgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;')
