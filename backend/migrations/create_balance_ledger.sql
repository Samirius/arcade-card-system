-- Migration: Create balance ledger tables (AR-2)
-- This migration creates the balance ledger and snapshot tables for server-authoritative balance management

-- Create balance_ledger table
CREATE TABLE IF NOT EXISTS balance_ledger (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_uid VARCHAR(255) NOT NULL,
    company_id UUID,
    transaction_id UUID REFERENCES transactions(id),
    amount DECIMAL(10, 2) NOT NULL,
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id),
    notes VARCHAR(500),
    reason_code VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create balance_snapshots table
CREATE TABLE IF NOT EXISTS balance_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_uid VARCHAR(255) NOT NULL,
    company_id UUID,
    balance DECIMAL(10, 2) NOT NULL,
    snapshot_type VARCHAR(50) NOT NULL,
    total_transactions INTEGER NOT NULL DEFAULT 0,
    total_additions DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_deductions DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_refunds DECIMAL(10, 2) NOT NULL DEFAULT 0,
    snapshot_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for ledger
CREATE INDEX IF NOT EXISTS idx_ledger_card_date ON balance_ledger(card_uid, created_at, operation_type);
CREATE INDEX IF NOT EXISTS idx_ledger_company_date ON balance_ledger(company_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ledger_transaction ON balance_ledger(transaction_id);
CREATE INDEX IF NOT EXISTS idx_ledger_user_date ON balance_ledger(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ledger_reason_code ON balance_ledger(reason_code);

-- Create indexes for snapshots
CREATE INDEX IF NOT EXISTS idx_snapshots_card_date ON balance_snapshots(card_uid, snapshot_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_company_type ON balance_snapshots(company_id, snapshot_type, snapshot_at);

-- Add comments for documentation
COMMENT ON TABLE balance_ledger IS 'Immutable ledger tracking all balance changes with audit trail';
COMMENT ON COLUMN balance_ledger.amount IS 'Amount changed (positive for add, negative for deduct)';
COMMENT ON COLUMN balance_ledger.balance_before IS 'Balance before change';
COMMENT ON COLUMN balance_ledger.balance_after IS 'Balance after change';
COMMENT ON COLUMN balance_ledger.operation_type IS 'Type: ADD, DEDUCT, REFUND, ADJUSTMENT, ADD_ROLLBACK, DEDUCT_ROLLBACK';
COMMENT ON COLUMN balance_ledger.reason_code IS 'For disputes and reversals (ROLLBACK, DISPUTE, etc)';
COMMENT ON COLUMN balance_ledger.metadata IS 'Flexible context data (machine_id, location, etc)';
COMMENT ON TABLE balance_snapshots IS 'Periodic balance snapshots for historical reporting';
COMMENT ON COLUMN balance_snapshots.snapshot_type IS 'HOURLY, DAILY, WEEKLY, MONTHLY';
COMMENT ON COLUMN balance_snapshots.total_transactions IS 'Number of transactions since last snapshot';

-- Create function to automatically update transaction reference in ledger
CREATE OR REPLACE FUNCTION update_transaction_ledger_reference()
RETURNS TRIGGER AS $$
BEGIN
    -- Update ledger entries to reference the new transaction
    UPDATE balance_ledger
    SET transaction_id = NEW.id
    WHERE card_uid = NEW.card_uid
      AND transaction_id IS NULL
      AND created_at >= NOW() - INTERVAL '1 second';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to link ledger entries to transactions
DROP TRIGGER IF EXISTS trigger_link_transaction_ledger ON transactions;
CREATE TRIGGER trigger_link_transaction_ledger
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_transaction_ledger_reference();

-- Create function to create automatic daily snapshots
CREATE OR REPLACE FUNCTION create_daily_balance_snapshot()
RETURNS VOID AS $$
DECLARE
    card_record RECORD;
    card_balance DECIMAL;
    company_id_val UUID;
BEGIN
    -- Iterate through all active cards
    FOR card_record IN
        SELECT DISTINCT card_uid, company_id
        FROM cards
        WHERE status = 'ACTIVE'
    LOOP
        -- Get current balance
        SELECT balance, company_id INTO card_balance, company_id_val
        FROM cards
        WHERE card_uid = card_record.card_uid;

        -- Create snapshot if one doesn't exist today
        INSERT INTO balance_snapshots (
            card_uid,
            company_id,
            balance,
            snapshot_type,
            total_transactions,
            total_additions,
            total_deductions,
            total_refunds,
            snapshot_at
        )
        SELECT
            card_record.card_uid,
            company_id_val,
            card_balance,
            'DAILY',
            COUNT(*),
            COALESCE(SUM(CASE WHEN operation_type = 'ADD' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN operation_type = 'DEDUCT' THEN ABS(amount) ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN operation_type = 'REFUND' THEN amount ELSE 0 END), 0),
            NOW()
        FROM balance_ledger
        WHERE card_uid = card_record.card_uid
          AND created_at >= DATE_TRUNC('day', NOW())
        ON CONFLICT DO NOTHING;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Note: Schedule this function to run daily using pg_cron or external job scheduler
-- Example: SELECT cron.schedule('0 2 * * *', $$SELECT create_daily_balance_snapshot()$$);