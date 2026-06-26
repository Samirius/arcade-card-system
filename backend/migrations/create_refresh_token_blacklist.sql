-- Refresh Token Blacklist Table
-- Stores hashes of revoked refresh tokens to prevent reuse

CREATE TABLE IF NOT EXISTS refresh_token_blacklist (
    id VARCHAR(36) PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    revocation_reason VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_refresh_blacklist_token_hash ON refresh_token_blacklist(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_blacklist_expires_at ON refresh_token_blacklist(expires_at);
CREATE INDEX IF NOT EXISTS idx_refresh_blacklist_user_id ON refresh_token_blacklist(user_id);

-- Comment
COMMENT ON TABLE refresh_token_blacklist IS 'Blacklist for revoked refresh tokens to prevent reuse';