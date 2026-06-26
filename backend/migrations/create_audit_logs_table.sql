-- Create audit logs table for security auditing
-- Run this in PostgreSQL: psql -d arcade_management -f migrations/create_audit_logs_table.sql

CREATE TYPE audit_action AS ENUM (
    'LOGIN',
    'LOGOUT',
    'CREATE',
    'READ',
    'UPDATE',
    'DELETE',
    'TRANSACTION',
    'REFUND',
    'CONFIG_CHANGE',
    'FAILED_LOGIN'
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    action audit_action NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    old_values JSONB,
    new_values JSONB,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_date ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);