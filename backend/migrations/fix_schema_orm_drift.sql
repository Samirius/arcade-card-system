-- Migration: Fix Schema/ORM Drift (BE-7) — REVISED
-- Aligns database schema with SQLAlchemy ORM definitions.
-- Safe to run on an existing database.

-- 1. Add token_version column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

-- 2. Fix failed_login_attempts type (was VARCHAR → should be INTEGER)
-- Only run if the column is still varchar (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users'
          AND column_name = 'failed_login_attempts'
          AND data_type = 'character varying'
    ) THEN
        ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts_new INTEGER NOT NULL DEFAULT 0;
        UPDATE users SET failed_login_attempts_new = CAST(NULLIF(failed_login_attempts, '') AS INTEGER);
        ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts;
        ALTER TABLE users RENAME COLUMN failed_login_attempts_new TO failed_login_attempts;
    END IF;
END $$;

-- 3. Fix user_role enum to match ORM (UserRole: STAFF, SUPERVISOR, REGIONAL_MGR, ADMIN, OWNER)
-- The ORM defines exactly these 5 roles. We must NOT add extra labels.
-- Only add labels that are missing; never DROP the type while columns reference it.
DO $$
BEGIN
    -- Add missing labels without dropping the type
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'STAFF' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')) THEN
        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'STAFF';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'SUPERVISOR' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')) THEN
        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SUPERVISOR';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'REGIONAL_MGR' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')) THEN
        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'REGIONAL_MGR';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'ADMIN' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')) THEN
        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'ADMIN';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'OWNER' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')) THEN
        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'OWNER';
    END IF;
END $$;

-- 4. Fix user_status enum to match ORM (UserStatus: ACTIVE, INACTIVE, LOCKED, PENDING)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'ACTIVE' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_status')) THEN
        ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'ACTIVE';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'INACTIVE' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_status')) THEN
        ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'INACTIVE';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'LOCKED' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_status')) THEN
        ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'LOCKED';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PENDING' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_status')) THEN
        ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'PENDING';
    END IF;
END $$;

-- 5. Create performance indexes
CREATE INDEX IF NOT EXISTS idx_users_token_version ON users(token_version);
CREATE INDEX IF NOT EXISTS idx_users_failed_attempts ON users(failed_login_attempts);

COMMENT ON COLUMN users.token_version IS 'Token version incremented on logout to invalidate all tokens';
COMMENT ON COLUMN users.failed_login_attempts IS 'Number of failed login attempts (integer)';
