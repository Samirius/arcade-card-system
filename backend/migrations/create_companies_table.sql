-- Migration: Create companies table for multi-tenancy (AR-1)
-- This migration creates the companies table to support multi-tenant SaaS architecture

-- Create company plan enum
CREATE TYPE company_plan AS ENUM (
    'STARTER',
    'PRO',
    'ENTERPRISE'
);

-- Create company status enum
CREATE TYPE company_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'SUSPENDED',
    'DELETED'
);

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address VARCHAR(500),
    city VARCHAR(100),
    country VARCHAR(100),
    business_type VARCHAR(50),
    tax_id VARCHAR(50),
    plan company_plan NOT NULL DEFAULT 'STARTER',
    status company_status NOT NULL DEFAULT 'ACTIVE',
    max_venues INTEGER NOT NULL DEFAULT 1,
    max_users INTEGER NOT NULL DEFAULT 10,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID REFERENCES users(id)
);

-- Add company_id to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id);
CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id);

-- Add company_id to cards table
ALTER TABLE cards ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id);
CREATE INDEX IF NOT EXISTS idx_cards_company_id ON cards(company_id);

-- Add company_id to transactions table
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id);
CREATE INDEX IF NOT EXISTS idx_transactions_company_id ON transactions(company_id);

-- Create composite indexes for tenant isolation
CREATE INDEX IF NOT EXISTS idx_users_company_status ON users(company_id, status);
CREATE INDEX IF NOT EXISTS idx_cards_company_status ON cards(company_id, status);
CREATE INDEX IF NOT EXISTS idx_transactions_company_date ON transactions(company_id, created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE companies IS 'Tenant companies for multi-tenant SaaS architecture';
COMMENT ON COLUMN companies.slug IS 'URL-friendly unique identifier for company';
COMMENT ON COLUMN companies.plan IS 'Subscription plan: STARTER (10 users, 1 venue), PRO (50 users, 5 venues), ENTERPRISE (unlimited)';
COMMENT ON COLUMN companies.max_users IS 'Maximum number of users allowed by plan';
COMMENT ON COLUMN companies.max_venues IS 'Maximum number of venues allowed by plan';
COMMENT ON COLUMN users.company_id IS 'Company ID for tenant isolation (NULL = super-admin)';
COMMENT ON COLUMN cards.company_id IS 'Company ID for tenant isolation';
COMMENT ON COLUMN transactions.company_id IS 'Company ID for tenant isolation';

-- Plan limit configurations (stored as table for easy updates)
CREATE TABLE IF NOT EXISTS company_plan_limits (
    plan company_plan PRIMARY KEY,
    max_users INTEGER,
    max_venues INTEGER,
    max_cards INTEGER,
    max_transactions_month INTEGER,
    support_level VARCHAR(50)
);

INSERT INTO company_plan_limits (plan, max_users, max_venues, max_cards, max_transactions_month, support_level) VALUES
    ('STARTER', 10, 1, 1000, 10000, 'email')
ON CONFLICT (plan) DO NOTHING;

INSERT INTO company_plan_limits (plan, max_users, max_venues, max_cards, max_transactions_month, support_level) VALUES
    ('PRO', 50, 5, 5000, 50000, 'priority')
ON CONFLICT (plan) DO NOTHING;

INSERT INTO company_plan_limits (plan, max_users, max_venues, max_cards, max_transactions_month, support_level) VALUES
    ('ENTERPRISE', NULL, NULL, NULL, NULL, 'dedicated')
ON CONFLICT (plan) DO NOTHING;