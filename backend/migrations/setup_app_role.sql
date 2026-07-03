-- ===========================================================================
-- setup_app_role.sql  — non-superuser application role for RLS enforcement
-- ===========================================================================
--
-- BE-1: PostgreSQL Row-Level Security (RLS) tenant isolation.
--
-- WHY THIS FILE EXISTS
-- --------------------
-- RLS policies (see the `rls_tenant_isolation_0001` Alembic migration) are
-- IGNORED for PostgreSQL superusers and for any role with the BYPASSRLS
-- attribute. The current app role in some environments (`arcade_user`) is a
-- SUPERUSER, so RLS would silently do nothing for it.
--
-- This script provisions a dedicated, least-privilege login role, `arcade_app`,
-- that is NOSUPERUSER + NOBYPASSRLS. When the application connects AS this role,
-- the RLS policies actually take effect and the per-request tenant GUCs
-- (`app.tenant_id`, `app.is_superadmin`, set via SET LOCAL in the auth
-- dependencies) scope every query to the caller's company.
--
-- PRODUCTION REQUIREMENT
-- ----------------------
-- For RLS to take effect in production, `DATABASE_URL` MUST point at
-- `arcade_app` (a NON-superuser), e.g.:
--
--     DATABASE_URL=postgresql://arcade_app:<password>@<host>:<port>/arcade_management
--
-- If `DATABASE_URL` keeps using a superuser (e.g. `arcade_user`), the app will
-- still function but RLS will be bypassed and tenant isolation will NOT be
-- enforced at the database layer.
--
-- HOW TO RUN
-- ----------
-- Run as a superuser (e.g. `arcade_user`), AFTER the schema/tables exist and
-- after `alembic upgrade head` has created the policies:
--
--     psql "$SUPERUSER_DATABASE_URL" -v ON_ERROR_STOP=1 \
--          -f backend/migrations/setup_app_role.sql
--
-- The password below is a development placeholder. In production, create the
-- role with a real secret (e.g. `ALTER ROLE arcade_app WITH PASSWORD '...';`)
-- or provision it out-of-band and keep this file's grants only.
--
-- This script is idempotent and safe to re-run (it re-applies grants, which is
-- what you want after new tables are added).
-- ===========================================================================

-- 1) Create the least-privilege login role if it does not already exist.
--    LOGIN         — can connect
--    NOSUPERUSER   — not a superuser (superusers bypass RLS)
--    NOBYPASSRLS   — explicitly subject to row-level security policies
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'arcade_app') THEN
        CREATE ROLE arcade_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD 'arcade_app_password';
    ELSE
        -- Ensure the attributes are correct even if the role pre-existed.
        ALTER ROLE arcade_app WITH LOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

-- 2) Allow the role to connect to the database and use the public schema.
--    (current_database() keeps this portable across environments.)
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO arcade_app', current_database());
END
$$;

GRANT USAGE ON SCHEMA public TO arcade_app;

-- 3) Grant CRUD on all existing tables in schema public.
--    RLS still constrains WHICH rows arcade_app can touch; these grants only
--    say it may operate on the tables at all.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO arcade_app;

-- 4) Grant sequence access so INSERTs that use serial/identity/uuid-default
--    sequences work (USAGE for nextval, SELECT for currval).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO arcade_app;

-- 5) Make future tables/sequences (created later by migrations or create_all)
--    automatically grant the same privileges to arcade_app, so operators do not
--    have to re-run this after every schema change.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO arcade_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO arcade_app;
