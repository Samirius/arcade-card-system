-- Migration: Add missing token_version column (BE-7 part 1)
-- This migration adds the token_version column to the users table
-- It fixes the schema/ORM drift where the model has token_version but the database doesn't

-- Add token_version column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

-- Create index on token_version for performance
CREATE INDEX IF NOT EXISTS idx_users_token_version ON users(token_version);

COMMENT ON COLUMN users.token_version IS 'Token version incremented on logout to invalidate all tokens';