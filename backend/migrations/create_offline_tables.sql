-- Migration: Create offline tokens and transactions tables (AR-3)
-- This migration creates tables for offline device operation support

-- Create offline_tokens table
CREATE TABLE IF NOT EXISTS offline_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id VARCHAR(255) UNIQUE NOT NULL,
    card_uid VARCHAR(255) NOT NULL,
    company_id UUID,
    balance INTEGER NOT NULL,  -- Stored as cents (integer)
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    device_id VARCHAR(255),
    token_version INTEGER NOT NULL DEFAULT 1,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by UUID REFERENCES users(id),
    revocation_reason VARCHAR(500),
    used_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create offline_transactions table
CREATE TABLE IF NOT EXISTS offline_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_uid VARCHAR(255) NOT NULL,
    company_id UUID,
    amount INTEGER NOT NULL,  -- Stored as cents (integer)
    transaction_type VARCHAR(50) NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    offline_token_id VARCHAR(255) NOT NULL,
    machine_id VARCHAR(255),
    location_id VARCHAR(255),
    device_timestamp TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    synced_at TIMESTAMP WITH TIME ZONE,
    rejection_reason VARCHAR(500),
    server_transaction_id UUID REFERENCES transactions(id),
    device_signature VARCHAR(255),
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for offline_tokens
CREATE INDEX IF NOT EXISTS idx_offline_tokens_card_active ON offline_tokens(card_uid, is_revoked);
CREATE INDEX IF NOT EXISTS idx_offline_tokens_device_active ON offline_tokens(device_id, is_revoked);
CREATE INDEX IF NOT EXISTS idx_offline_tokens_expiry ON offline_tokens(expires_at, is_revoked);

-- Create indexes for offline_transactions
CREATE INDEX IF NOT EXISTS idx_offline_tx_sync_status ON offline_transactions(sync_status, created_at);
CREATE INDEX IF NOT EXISTS idx_offline_tx_device_pending ON offline_transactions(device_id, sync_status);
CREATE INDEX IF NOT EXISTS idx_offline_tx_company_pending ON offline_transactions(company_id, sync_status);

-- Add comments for documentation
COMMENT ON TABLE offline_tokens IS 'Signed JWT tokens for offline device play - revocable, expiring';
COMMENT ON COLUMN offline_tokens.token_id IS 'JWT jti claim - unique token identifier';
COMMENT ON COLUMN offline_tokens.balance IS 'Balance in cents (integer) at token issuance';
COMMENT ON COLUMN offline_tokens.device_id IS 'Device fingerprint for device binding';
COMMENT ON COLUMN offline_tokens.is_revoked IS '0 = active, 1 = revoked (bit field)';
COMMENT ON COLUMN offline_tokens.used_count IS 'Number of times token has been validated/used';
COMMENT ON TABLE offline_transactions IS 'Transactions created offline, queued for server sync';
COMMENT ON COLUMN offline_transactions.sync_status IS 'PENDING, SYNCED, REJECTED';
COMMENT ON COLUMN offline_transactions.verification_status IS 'PENDING, VERIFIED, FAILED';
COMMENT ON COLUMN offline_transactions.device_signature IS 'Device-signed hash for verification';

-- Create function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired and revoked tokens older than 7 days
    DELETE FROM offline_tokens
    WHERE is_revoked = 1
      AND revoked_at < NOW() - INTERVAL '7 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to auto-reject stale pending transactions
CREATE OR REPLACE FUNCTION reject_stale_pending_transactions()
RETURNS INTEGER AS $$
DECLARE
    rejected_count INTEGER;
BEGIN
    -- Reject transactions pending for more than 24 hours
    UPDATE offline_transactions
    SET sync_status = 'REJECTED',
        rejection_reason = 'Transaction expired - pending too long',
        updated_at = NOW()
    WHERE sync_status = 'PENDING'
      AND created_at < NOW() - INTERVAL '24 hours';

    GET DIAGNOSTICS rejected_count = ROW_COUNT;

    RETURN rejected_count;
END;
$$ LANGUAGE plpgsql;

-- Note: Schedule these functions using pg_cron or external job scheduler
-- Example:
-- SELECT cron.schedule('0 2 * * *', $$SELECT cleanup_expired_tokens()$$);
-- SELECT cron.schedule('0 */6 * * *', $$SELECT reject_stale_pending_transactions()$$);

-- Create view for monitoring offline queue status
CREATE OR REPLACE VIEW v_offline_queue_status AS
SELECT
    company_id,
    device_id,
    COUNT(*) FILTER (WHERE sync_status = 'PENDING') as pending_count,
    COUNT(*) FILTER (WHERE sync_status = 'SYNCED') as synced_count,
    COUNT(*) FILTER (WHERE sync_status = 'REJECTED') as rejected_count,
    SUM(amount) FILTER (WHERE sync_status = 'PENDING') as pending_amount_cents,
    MAX(created_at) FILTER (WHERE sync_status = 'PENDING') as oldest_pending_at,
    MAX(synced_at) FILTER (WHERE sync_status = 'SYNCED') as last_sync_at
FROM offline_transactions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY company_id, device_id;

COMMENT ON VIEW v_offline_queue_status IS 'Monitoring view for offline sync queue status by device';

-- Create view for active offline tokens
CREATE OR REPLACE VIEW v_active_offline_tokens AS
SELECT
    company_id,
    card_uid,
    device_id,
    COUNT(*) as active_tokens,
    MIN(issued_at) as oldest_issued_at,
    MAX(expires_at) as furthest_expires_at,
    SUM(used_count) as total_uses
FROM offline_tokens
WHERE is_revoked = 0
  AND expires_at > NOW()
GROUP BY company_id, card_uid, device_id;

COMMENT ON VIEW v_active_offline_tokens IS 'Monitoring view for currently active offline tokens';