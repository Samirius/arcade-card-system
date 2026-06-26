-- Create User, Card, and Transaction tables
-- Run: cat migrations/create_tables.sql | sudo -u postgres psql -d arcade_management

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create Enums
CREATE TYPE user_role AS ENUM (
    'STAFF',
    'SUPERVISOR',
    'REGIONAL_MGR',
    'ADMIN',
    'OWNER'
);

CREATE TYPE user_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'LOCKED',
    'PENDING'
);

CREATE TYPE card_type AS ENUM (
    'REGULAR',
    'VIP',
    'STAFF',
    'TEST'
);

CREATE TYPE card_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'LOST',
    'STOLEN',
    'DAMAGED'
);

-- Create Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role user_role NOT NULL DEFAULT 'STAFF',
    status user_status NOT NULL DEFAULT 'PENDING',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    backup_codes VARCHAR(255)[],
    failed_login_attempts VARCHAR(10) NOT NULL DEFAULT '0',
    last_login TIMESTAMP WITH TIME ZONE,
    last_failed_login TIMESTAMP WITH TIME ZONE,
    locked_until TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    force_password_change BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create Cards table
CREATE TABLE IF NOT EXISTS cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_uid VARCHAR(255) UNIQUE NOT NULL,
    owner VARCHAR(100) NOT NULL,
    card_type card_type NOT NULL DEFAULT 'REGULAR',
    status card_status NOT NULL DEFAULT 'ACTIVE',
    balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    notes VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_transaction_at TIMESTAMP WITH TIME ZONE
);

-- Create Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_uid VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    payment_method VARCHAR(50),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notes VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for Users
CREATE INDEX idx_users_email_lower ON users (email varchar_pattern_ops);
CREATE INDEX idx_users_role_status ON users (role, status);
CREATE INDEX idx_users_status_active ON users (status);

-- Create Indexes for Cards
CREATE INDEX idx_cards_uid_type ON cards (card_uid, card_type);
CREATE INDEX idx_cards_owner_status ON cards (owner, status);
CREATE INDEX idx_cards_type_status ON cards (card_type, status);

-- Create Indexes for Transactions
CREATE INDEX idx_transactions_card_date ON transactions (card_uid, created_at DESC);
CREATE INDEX idx_transactions_type_date ON transactions (transaction_type, created_at DESC);
CREATE INDEX idx_transactions_user_date ON transactions (user_id, created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE users IS 'User accounts with roles, status, and MFA';
COMMENT ON TABLE cards IS 'Arcade cards with balance tracking';
COMMENT ON TABLE transactions IS 'Card balance transactions';

COMMENT ON COLUMN users.role IS 'Hierarchical roles: STAFF < SUPERVISOR < REGIONAL_MGR < ADMIN < OWNER';
COMMENT ON COLUMN users.status IS 'Account status: ACTIVE, INACTIVE, LOCKED, PENDING';
COMMENT ON COLUMN users.mfa_enabled IS 'Multi-factor authentication enabled';
COMMENT ON COLUMN users.locked_until IS 'Account locked until this timestamp';

COMMENT ON COLUMN cards.card_type IS 'Card types: REGULAR, VIP, STAFF, TEST';
COMMENT ON COLUMN cards.balance IS 'Card balance in currency units';

COMMENT ON COLUMN transactions.transaction_type IS 'Transaction types: ADD, DEDUCT, REFUND';