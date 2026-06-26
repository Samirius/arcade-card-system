-- Migration: Fix Schema/ORM Drift (BE-7)
-- This migration adds missing columns and fixes type mismatches

-- Add token_version column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

-- Fix failed_login_attempts type (VARCHAR(10) -> INTEGER)
-- First create a temporary column with the right type
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts_new INTEGER NOT NULL DEFAULT 0;

-- Copy data from old column to new column
UPDATE users SET failed_login_attempts_new = CAST(failed_login_attempts AS INTEGER);

-- Drop old column
ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts;

-- Rename new column to the correct name
ALTER TABLE users RENAME COLUMN failed_login_attempts_new TO failed_login_attempts;

-- Add proper ENUM values (add missing roles)
DROP TYPE IF EXISTS user_role;
CREATE TYPE user_role AS ENUM (
    'CUSTOMER',
    'STAFF',
    'SUPERVISOR',
    'REGIONAL_MGR',
    'OPERATIONS',
    'ADMIN',
    'OWNER'
);

-- Add missing user status values
DROP TYPE IF EXISTS user_status;
CREATE TYPE user_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'LOCKED',
    'PENDING_VERIFICATION',
    'DELETED'
);

-- Add proper enum values for card types
DROP TYPE IF EXISTS card_type;
CREATE TYPE card_type AS ENUM (
    'REGULAR',
    'VIP',
    'STAFF',
    'TEST'
);

-- Add proper enum values for card status
DROP TYPE IF EXISTS card_status;
CREATE TYPE card_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'LOST',
    'STOLEN',
    'DAMAGED'
);

-- Create index on token_version for performance
CREATE INDEX IF NOT EXISTS idx_users_token_version ON users(token_version);

-- Create index on failed_login_attempts
CREATE INDEX IF NOT EXISTS idx_users_failed_attempts ON users(failed_login_attempts);

COMMENT ON COLUMN users.token_version IS 'Token version incremented on logout to invalidate all tokens';
COMMENT ON COLUMN users.failed_login_attempts IS 'Number of failed login attempts (integer)';
COMMENT ON TABLE refresh_token_blacklist IS 'Revoked refresh tokens to prevent reuse';