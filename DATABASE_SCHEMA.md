# Arcade Management System - Database Schema

## 📊 Entity Relationship Overview

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Companies  │──────▶│  Locations  │──────▶│    Cards    │
└─────────────┘       └─────────────┘       └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Regions   │       │  Machines   │       │Transac-    │
└─────────────┘       └─────────────┘       │  tions    │
                                             └─────────────┘
                                                    │
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Users     │──────▶│  Permissions│◀──────│  Staff     │
└─────────────┘       └─────────────┘       └─────────────┘
       │
       ▼
┌─────────────┐
│ Customers   │
└─────────────┘
```

---

## 🗄️ Core Tables (MVP)

### 1. users
**Purpose:** All system users (staff, supervisors, admins)

```sql
CREATE TYPE user_role AS ENUM (
    'CUSTOMER',      -- Level 1
    'STAFF',         -- Level 2
    'SUPERVISOR',    -- Level 3
    'REGIONAL_MGR',  -- Level 4
    'OPERATIONS',    -- Level 5
    'ADMIN',         -- Level 6
    'OWNER'          -- Level 7
);

CREATE TYPE user_status AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'PENDING_VERIFICATION',
    'DELETED'
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    role user_role NOT NULL,
    status user_status DEFAULT 'PENDING_VERIFICATION',
    location_id UUID REFERENCES locations(id),
    region_id UUID REFERENCES regions(id),
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    last_login TIMESTAMP,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_location ON users(location_id);
CREATE INDEX idx_users_status ON users(status);

-- Triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2. customers
**Purpose:** Customer profile data (separate from cards)

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id), -- Optional: if they have an account
    email VARCHAR(255),
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(50),
    preferred_language VARCHAR(10) DEFAULT 'en',
    marketing_consent BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_name ON customers(first_name, last_name);
```

### 3. cards
**Purpose:** Physical/virtual cards (RFID, QR, mobile)

```sql
CREATE TYPE card_type AS ENUM (
    'REGULAR',
    'VIP',
    'STAFF',
    'MANAGEMENT'
);

CREATE TYPE card_status AS ENUM (
    'ACTIVE',
    'BLOCKED',
    'LOST',
    'STOLEN',
    'EXPIRED',
    'DELETED'
);

CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    card_uid VARCHAR(255) UNIQUE NOT NULL, -- Tokenized RFID UID
    card_uid_hash VARCHAR(255) UNIQUE NOT NULL, -- Hashed for quick lookup
    card_type card_type DEFAULT 'REGULAR',
    status card_status DEFAULT 'ACTIVE',
    balance DECIMAL(10,2) DEFAULT 0.00 CHECK (balance >= 0),
    location_id UUID REFERENCES locations(id),
    issued_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    last_used TIMESTAMP,
    last_location_id UUID REFERENCES locations(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_cards_uid ON cards(card_uid);
CREATE INDEX idx_cards_uid_hash ON cards(card_uid_hash);
CREATE INDEX idx_cards_customer ON cards(customer_id);
CREATE INDEX idx_cards_type ON cards(card_type);
CREATE INDEX idx_cards_status ON cards(status);
CREATE INDEX idx_cards_location ON cards(location_id);

-- Triggers
CREATE TRIGGER update_cards_updated_at
    BEFORE UPDATE ON cards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cards_last_used
    BEFORE UPDATE ON cards
    FOR EACH ROW
    WHEN (OLD.balance IS DISTINCT FROM NEW.balance)
    EXECUTE FUNCTION update_last_used();
```

### 4. transactions
**Purpose:** All financial transactions

```sql
CREATE TYPE transaction_type AS ENUM (
    'ADD',           -- Staff adding credits
    'DEDUCT',        -- Machine deducting credits
    'REFUND',        -- Supervisor refunding
    'TRANSFER',      -- Transfer between cards
    'ADJUSTMENT',    -- Admin adjustment
    'REVERSAL'       -- Reversing a transaction
);

CREATE TYPE payment_method AS ENUM (
    'CASH',
    'CREDIT_CARD',
    'DEBIT_CARD',
    'DIGITAL_WALLET',
    'TRANSFER',
    'VOUCHER',
    'INTERNAL'
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES cards(id) NOT NULL,
    location_id UUID REFERENCES locations(id) NOT NULL,
    machine_id UUID REFERENCES machines(id), -- NULL = manual transaction
    transaction_type transaction_type NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    balance_before DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2) NOT NULL,
    payment_method payment_method DEFAULT 'INTERNAL',
    staff_id UUID REFERENCES users(id),
    original_transaction_id UUID REFERENCES transactions(id), -- For reversals
    reference_number VARCHAR(100), -- External payment reference
    notes TEXT,
    metadata JSONB, -- Flexible data for future features
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_transactions_card ON transactions(card_id);
CREATE INDEX idx_transactions_location ON transactions(location_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_date ON transactions(created_at);
CREATE INDEX idx_transactions_staff ON transactions(staff_id);

-- Check: Balance never negative
ALTER TABLE cards ADD CONSTRAINT check_balance_non_negative
    CHECK (balance >= 0);

-- Check: Transaction amounts are positive
ALTER TABLE transactions ADD CONSTRAINT check_amount_positive
    CHECK (amount > 0);
```

### 5. locations
**Purpose:** Physical locations (arcades, parks)

```sql
CREATE TYPE location_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'MAINTENANCE',
    'CLOSED'
);

CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    region_id UUID REFERENCES regions(id),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE, -- Short code for kiosks
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    phone VARCHAR(20),
    email VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    currency VARCHAR(3) DEFAULT 'USD',
    status location_status DEFAULT 'ACTIVE',
    opening_hours JSONB, -- Flexible hours structure
    geolocation POINT,
    settings JSONB, -- Location-specific settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_locations_company ON locations(company_id);
CREATE INDEX idx_locations_region ON locations(region_id);
CREATE INDEX idx_locations_status ON locations(status);
CREATE INDEX idx_locations_code ON locations(code);

-- Geography index for "find nearest" queries
CREATE INDEX idx_locations_geo ON locations USING GIST (geolocation);
```

### 6. machines
**Purpose:** Arcade machines, kiosks, attractions

```sql
CREATE TYPE machine_type AS ENUM (
    'GAME',
    'KIOSK',
    'ATTRACTION',
    'VENDING'
);

CREATE TYPE machine_status AS ENUM (
    'ONLINE',
    'OFFLINE',
    'MAINTENANCE',
    'OUT_OF_SERVICE',
    'RETIRED'
);

CREATE TABLE machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id UUID REFERENCES locations(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    serial_number VARCHAR(100) UNIQUE,
    machine_type machine_type NOT NULL,
    status machine_status DEFAULT 'ONLINE',
    cost_per_play DECIMAL(10,2) DEFAULT 1.00,
    revenue_total DECIMAL(12,2) DEFAULT 0.00,
    revenue_today DECIMAL(10,2) DEFAULT 0.00,
    play_count_total INT DEFAULT 0,
    play_count_today INT DEFAULT 0,
    last_maintenance TIMESTAMP,
    next_maintenance TIMESTAMP,
    firmware_version VARCHAR(50),
    certificate_id VARCHAR(255), -- For ESP32 auth
    last_seen TIMESTAMP,
    geolocation POINT,
    settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_machines_location ON machines(location_id);
CREATE INDEX idx_machines_type ON machines(machine_type);
CREATE INDEX idx_machines_status ON machines(machine_status);
CREATE INDEX idx_machines_serial ON machines(serial_number);
CREATE INDEX idx_machines_certificate ON machines(certificate_id);
```

### 7. audit_logs
**Purpose:** Audit trail for compliance and security

```sql
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

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action audit_action NOT NULL,
    resource_type VARCHAR(100), -- 'card', 'transaction', 'user', etc.
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    old_values JSONB,
    new_values JSONB,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_date ON audit_logs(created_at);

-- Partition by month for performance (optional for Phase 2)
-- CREATE TABLE audit_logs_2024_06 PARTITION OF audit_logs
--     FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
```

### 8. companies
**Purpose:** Multi-tenant support (Phase 2+)

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE,
    subscription_tier VARCHAR(50) DEFAULT 'STARTER',
    settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 9. regions
**Purpose:** Group locations by region

```sql
CREATE TABLE regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    name VARCHAR(255) NOT NULL,
    manager_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔐 Security Functions & Triggers

### Update Timestamp Trigger
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Update Last Used Trigger
```sql
CREATE OR REPLACE FUNCTION update_last_used()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_used = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Card Balance Validation Trigger
```sql
CREATE OR REPLACE FUNCTION validate_card_balance()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.balance < 0 THEN
        RAISE EXCEPTION 'Card balance cannot be negative';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_balance
    BEFORE INSERT OR UPDATE ON cards
    FOR EACH ROW
    EXECUTE FUNCTION validate_card_balance();
```

### Transaction Logging Trigger
```sql
CREATE OR REPLACE FUNCTION log_transaction_audit()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        user_id,
        action,
        resource_type,
        resource_id,
        new_values
    ) VALUES (
        NEW.created_by,
        'TRANSACTION',
        'transaction',
        NEW.id,
        jsonb_build_object(
            'card_id', NEW.card_id,
            'type', NEW.transaction_type,
            'amount', NEW.amount
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_transaction
    AFTER INSERT ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION log_transaction_audit();
```

---

## 📊 Views (Read-Only Data)

### Current Card Balances
```sql
CREATE VIEW v_card_balances AS
SELECT
    c.id,
    c.card_uid,
    c.card_type,
    c.status,
    c.balance,
    cu.first_name,
    cu.last_name,
    cu.email,
    l.name AS location_name,
    c.last_used
FROM cards c
LEFT JOIN customers cu ON c.customer_id = cu.id
LEFT JOIN locations l ON c.location_id = l.id
WHERE c.status != 'DELETED';
```

### Today's Revenue
```sql
CREATE VIEW v_today_revenue AS
SELECT
    l.id AS location_id,
    l.name AS location_name,
    COUNT(t.id) AS transaction_count,
    SUM(CASE WHEN t.transaction_type = 'DEDUCT' THEN t.amount ELSE 0 END) AS deductions,
    SUM(CASE WHEN t.transaction_type = 'ADD' THEN t.amount ELSE 0 END) AS additions,
    SUM(CASE WHEN t.transaction_type = 'DEDUCT' THEN t.amount ELSE 0 END) -
    SUM(CASE WHEN t.transaction_type = 'ADD' THEN t.amount ELSE 0 END) AS net_revenue
FROM transactions t
JOIN locations l ON t.location_id = l.id
WHERE DATE(t.created_at) = CURRENT_DATE
GROUP BY l.id, l.name;
```

### Active Machines
```sql
CREATE VIEW v_active_machines AS
SELECT
    m.id,
    m.name,
    m.machine_type,
    l.name AS location_name,
    m.status,
    m.revenue_today,
    m.play_count_today,
    m.last_seen
FROM machines m
JOIN locations l ON m.location_id = l.id
WHERE m.status = 'ONLINE';
```

---

## 🔍 Useful Queries

### Find card by UID (hashed lookup)
```sql
SELECT * FROM cards WHERE card_uid_hash = crypt('RFID_UID_HERE', gen_salt('bf'));
```

### Get card transaction history
```sql
SELECT
    t.id,
    t.transaction_type,
    t.amount,
    t.payment_method,
    t.balance_before,
    t.balance_after,
    l.name AS location,
    u.first_name AS staff_name,
    t.created_at
FROM transactions t
JOIN locations l ON t.location_id = l.id
LEFT JOIN users u ON t.staff_id = u.id
WHERE t.card_id = 'card_uuid_here'
ORDER BY t.created_at DESC;
```

### Daily revenue report
```sql
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS total_transactions,
    SUM(CASE WHEN transaction_type = 'DEDUCT' THEN amount ELSE 0 END) AS total_deductions,
    SUM(CASE WHEN transaction_type = 'ADD' THEN amount ELSE 0 END) AS total_additions,
    SUM(CASE WHEN transaction_type = 'DEDUCT' THEN amount ELSE 0 END) -
    SUM(CASE WHEN transaction_type = 'ADD' THEN amount ELSE 0 END) AS net_revenue
FROM transactions
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Staff performance (last 7 days)
```sql
SELECT
    u.first_name,
    u.last_name,
    COUNT(t.id) AS transactions_processed,
    SUM(t.amount) AS total_amount
FROM users u
JOIN transactions t ON u.id = t.staff_id
WHERE t.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY u.id, u.first_name, u.last_name
ORDER BY transactions_processed DESC;
```

---

## 🚀 Performance Optimizations

### 1. Partition Transactions by Month (Phase 2+)
```sql
-- Automatically create new partitions
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE + INTERVAL '1 month');
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'transactions_' || to_char(start_date, 'YYYY_MM');

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF transactions
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;
```

### 2. Materialized Views for Reports (Phase 4+)
```sql
CREATE MATERIALIZED VIEW mv_daily_revenue AS
SELECT
    DATE(t.created_at) AS date,
    t.location_id,
    l.name AS location_name,
    COUNT(*) FILTER (WHERE t.transaction_type = 'DEDUCT') AS deductions_count,
    SUM(t.amount) FILTER (WHERE t.transaction_type = 'DEDUCT') AS deductions_total,
    SUM(t.amount) FILTER (WHERE t.transaction_type = 'ADD') AS additions_total
FROM transactions t
JOIN locations l ON t.location_id = l.id
GROUP BY DATE(t.created_at), t.location_id, l.name;

-- Refresh daily
CREATE OR REPLACE FUNCTION refresh_daily_revenue()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_revenue;
END;
$$ LANGUAGE plpgsql;
```

---

## 📊 Database Statistics

### Estimated Data Growth (MVP)
- **Users:** 100-500 records = ~50 KB
- **Customers:** 500-2,000 records = ~200 KB
- **Cards:** 500-2,000 records = ~150 KB
- **Transactions:** 10,000-50,000/month = ~2-10 MB/month
- **Audit Logs:** 50,000-200,000/month = ~10-40 MB/month

### Storage Requirements (Year 1)
- Core tables: ~200 MB
- Audit logs: ~480 MB
- Indexes: ~300 MB
- Backups: 4x = ~4 GB
- **Total:** ~5 GB/year

---

## 🔒 Backup Strategy

### Automated Backups (daily)
```sql
-- Full backup
pg_dump -h localhost -U postgres -d arcade_system \
  -F c -f /backups/arcade_system_$(date +%Y%m%d).backup

-- Schema only
pg_dump -h localhost -U postgres -d arcade_system \
  --schema-only -f /backups/schema_$(date +%Y%m%d).sql
```

### Retention Policy
- Daily backups: 30 days
- Weekly backups: 12 weeks
- Monthly backups: 12 months
- Yearly backups: 7 years

---

This is a **production-ready database schema** designed for security, scalability, and audit compliance.

**Ready for Phase 1 development!** 🚀