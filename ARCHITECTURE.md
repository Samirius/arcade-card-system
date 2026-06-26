# Arcade Management System - Complete Architecture & Design

## 🎯 Project Vision

**"One system to rule them all"** - A comprehensive platform for managing any arcade, amusement park, or entertainment business.

---

## 📋 Phase 1: MVP (Card Reader System)

### Core Purpose
Manage customer cards, credits, and basic transactions for arcade machines.

### MVP Features
- ✅ Card registration (RFID)
- ✅ Credit balance management
- ✅ Basic transactions (add/deduct)
- ✅ Simple reporting (daily revenue)

### MVP Limitations (To Address Later)
- Single location
- Basic user roles only
- No scheduling
- No maintenance tracking
- Simple inventory

---

## 🏗️ Phase 2-5: Full System Roadmap

### Phase 2: Location Management
- Multiple locations/branches
- Location-level reporting
- Centralized admin
- Transfer cards between locations

### Phase 3: Machine & Maintenance
- Machine inventory tracking
- Maintenance scheduling
- Repair history
- Machine performance metrics
- Staff assignments

### Phase 4: Business Intelligence
- Advanced analytics
- Customer insights
- Revenue forecasting
- Peak time analysis
- Machine popularity ranking

### Phase 5: Enterprise Features
- Multi-company support
- Franchise management
- Advanced security
- API integrations
- White-label options

---

## 👥 User Types & Access Levels

### Hierarchy (Bottom-Up)

#### Level 1: Customers (Card Holders)
- **Access:** Check balance, view transactions, buy credits
- **Device:** RFID card, mobile app
- **Permissions:**
  - ✅ View own balance
  - ✅ View own transaction history
  - ✅ Request support
  - ❌ Cannot add credits (staff only)
  - ❌ Cannot view other cards
  - ❌ No admin access

#### Level 2: Staff (Front-line)
- **Roles:** Cashier, Floor Staff, Machine Attendant
- **Access:** Location-specific, limited scope
- **Permissions:**
  - ✅ Add credits to cards (cash payments)
  - ✅ Check card balances
  - ✅ View current transactions
  - ✅ Report machine issues
  - ✅ Daily sales reports
  - ❌ Cannot adjust card balances (no refunds)
  - ❌ Cannot view other locations
  - ❌ Cannot change prices

#### Level 3: Supervisors (Location Managers)
- **Roles:** Location Supervisor, Shift Manager
- **Access:** Single location, full control
- **Permissions:**
  - ✅ All staff permissions
  - ✅ Refund/adjust balances
  - ✅ Manage staff accounts
  - ✅ Access location reports
  - ✅ Schedule maintenance
  - ✅ View all cards at location
  - ✅ Cash drawer management
  - ❌ Cannot view other locations
  - ❌ Cannot change pricing

#### Level 4: Regional Managers
- **Roles:** Area Manager, Regional Director
- **Access:** Multiple locations (region)
- **Permissions:**
  - ✅ All supervisor permissions
  - ✅ View all locations in region
  - ✅ Regional reports & analytics
  - ✅ Compare location performance
  - ✅ Approve refunds above threshold
  - ✅ Transfer credits between locations
  - ❌ Cannot access other regions
  - ❌ Cannot change global pricing

#### Level 5: Operations
- **Roles:** Operations Manager, CFO, COO
- **Access:** All locations
- **Permissions:**
  - ✅ All regional manager permissions
  - ✅ Global reporting & analytics
  - ✅ Set pricing tiers
  - ✅ Manage card types (VIP, Regular)
  - ✅ Set refund policies
  - ✅ Approve large refunds
  - ✅ Export financial reports
  - ❌ Cannot access user accounts
  - ❌ Cannot change system settings

#### Level 6: IT/Admin (System Administrators)
- **Roles:** SysAdmin, Network Admin, Database Admin
- **Access:** All systems, technical control
- **Permissions:**
  - ✅ Manage all user accounts
  - ✅ Configure security settings
  - ✅ Manage API keys
  - ✅ System diagnostics
  - ✅ Database backups/restores
  - ✅ Log management
  - ✅ Technical support
  - ❌ Cannot access business data (separation of concerns)

#### Level 7: Owners/Executives
- **Roles:** CEO, Owner, Board Members
- **Access:** Everything (with audit trail)
- **Permissions:**
  - ✅ Full read access to all data
  - ✅ Executive dashboards
  - ✅ High-level reports
  - ✅ Financial statements
  - ✅ Strategic insights
  - ⚠️ All actions logged and audited
  - ⚠️ Cannot delete critical data

---

## 🔐 Security Architecture

### Authentication & Authorization

#### Multi-Factor Authentication (MFA)
- Level 4+: Mandatory MFA
- Level 3+: Optional but recommended
- Methods: SMS, Auth app, Hardware key

#### Session Management
- Token-based authentication (JWT)
- Session timeout: 30 min (staff), 8 hours (admin)
- IP-based restrictions for admin accounts
- Device fingerprinting
- Concurrent session limits

#### Access Control Matrix

| Feature | L1: Customer | L2: Staff | L3: Supervisor | L4: Regional | L5: Ops | L6: IT | L7: Owner |
|---------|--------------|-----------|----------------|--------------|--------|--------|----------|
| View own balance | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Add credits (cash) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Refund/adjust | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View location stats | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View regional stats | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Global reports | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| System settings | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Change pricing | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |

### Data Encryption

#### At Rest
- Database: AES-256 encryption
- Backups: AES-256 + separate encryption key
- Card data: Tokenized (never store raw card numbers)

#### In Transit
- HTTPS/TLS 1.3 only
- API: Encrypted endpoints
- ESP32: HTTPS with certificate pinning

#### Key Management
- Rotation policy: Every 90 days
- Secure storage: Hardware Security Module (HSM)
- Backup keys: Offline, air-gapped

### Audit Logging

#### What Gets Logged
- All user actions
- Balance changes (add/deduct/refund)
- Authentication events
- System configuration changes
- Failed access attempts
- Card creation/deletion

#### Log Retention
- Critical logs: 7 years (financial compliance)
- Access logs: 2 years
- System logs: 1 year
- Debug logs: 30 days

#### Log Storage
- WORM (Write Once, Read Many) storage
- Separate from primary database
- Regular integrity checks
- Tamper-evident (hashing)

### Network Security

#### Infrastructure
- VPC with private subnets
- Network segmentation (public, private, DMZ)
- Web Application Firewall (WAF)
- DDoS protection
- Rate limiting per IP/user

#### API Security
- API versioning (v1, v2, v3)
- Rate limiting: 100 req/min per user
- CORS restrictions
- Input validation & sanitization
- SQL injection prevention (ORM)
- XSS protection

#### Device Security
- ESP32: Certificate-based auth
- Readers: Network whitelisting
- Kiosks: Locked down OS, auto-logout
- Mobile apps: Code signing, app store only

---

## 📊 Database Architecture

### Data Segregation

```sql
-- Multi-tenancy with data isolation
tenants (companies)
├── locations
│   ├── cards
│   ├── transactions
│   ├── machines
│   └── staff_assignments
├── users
│   ├── customers
│   ├── staff
│   └── admins
└── global_settings
    ├── pricing_tiers
    ├── card_types
    └── system_configs
```

### Core Tables

#### Customers & Cards
```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    name VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE cards (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(id),
    card_uid VARCHAR(255) UNIQUE, -- RFID UID
    card_type VARCHAR(50), -- VIP, REGULAR, STAFF
    balance DECIMAL(10,2) DEFAULT 0,
    location_id UUID REFERENCES locations(id),
    status VARCHAR(20), -- ACTIVE, LOST, STOLEN, BLOCKED
    created_at TIMESTAMP,
    last_used TIMESTAMP
);
```

#### Locations & Hierarchy
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    subscription_tier VARCHAR(50),
    settings JSONB
);

CREATE TABLE locations (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    region_id UUID REFERENCES regions(id),
    name VARCHAR(255),
    address TEXT,
    timezone VARCHAR(50),
    status VARCHAR(20),
    created_at TIMESTAMP
);

CREATE TABLE regions (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    name VARCHAR(255),
    manager_id UUID REFERENCES users(id)
);
```

#### Users & Permissions
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role_level INT, -- 1-7
    location_id UUID REFERENCES locations(id), -- NULL = global/regional
    region_id UUID REFERENCES regions(id),
    mfa_enabled BOOLEAN DEFAULT FALSE,
    status VARCHAR(20), -- ACTIVE, SUSPENDED, DELETED
    last_login TIMESTAMP,
    created_at TIMESTAMP
);

CREATE TABLE permissions (
    user_id UUID REFERENCES users(id),
    permission VARCHAR(100),
    granted_at TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    expires_at TIMESTAMP
);
```

#### Transactions & Accounting
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    card_id UUID REFERENCES cards(id),
    location_id UUID REFERENCES locations(id),
    machine_id UUID REFERENCES machines(id), -- NULL = manual transaction
    transaction_type VARCHAR(50), -- ADD, DEDUCT, REFUND, TRANSFER
    amount DECIMAL(10,2),
    payment_method VARCHAR(50), -- CASH, CARD, TRANSFER
    staff_id UUID REFERENCES users(id),
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

CREATE TABLE transaction_reversals (
    id UUID PRIMARY KEY,
    original_transaction_id UUID REFERENCES transactions(id),
    reversal_transaction_id UUID REFERENCES transactions(id),
    reason TEXT,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP
);
```

#### Machines & Maintenance
```sql
CREATE TABLE machines (
    id UUID PRIMARY KEY,
    location_id UUID REFERENCES locations(id),
    name VARCHAR(255),
    machine_type VARCHAR(100), -- GAME, KIOSK, ATTRACTION
    serial_number VARCHAR(100),
    status VARCHAR(50), -- ONLINE, OFFLINE, MAINTENANCE
    cost_per_play DECIMAL(10,2),
    revenue_total DECIMAL(12,2),
    last_maintenance TIMESTAMP,
    next_maintenance TIMESTAMP
);

CREATE TABLE maintenance_schedules (
    id UUID PRIMARY KEY,
    machine_id UUID REFERENCES machines(id),
    scheduled_for TIMESTAMP,
    type VARCHAR(50), -- ROUTINE, REPAIR, UPGRADE
    assigned_to UUID REFERENCES users(id),
    status VARCHAR(50),
    notes TEXT
);
```

---

## 🚀 Technical Stack

### MVP Phase
```
Frontend: React + TypeScript
Backend: FastAPI (Python)
Database: PostgreSQL
Auth: JWT + MFA
Hosting: Local + VPN (no public exposure)
Security: No public access yet
```

### Production Phase
```
Frontend: React/Next.js + TypeScript
Backend: FastAPI (Python) + Microservices
Database: PostgreSQL + Redis (caching)
Auth: OAuth 2.0 + SAML (SSO)
Hosting: VPS or cloud (AWS/GCP)
CDN: CloudFlare
Monitoring: Prometheus + Grafana
Logging: ELK Stack
```

---

## 📱 Device Integration

### RFID Readers (ESP32)
- Certificate-based authentication
- Offline mode (queue transactions)
- Auto-sync when online
- Firmware over-the-air (FOTA) updates

### Kiosk Stations
- Self-service credit purchase
- Card balance check
- QR code generation (for mobile app)
- Receipt printing

### Mobile App (Customer)
- View balance
- Transaction history
- Purchase credits
- Find nearby locations
- Loyalty rewards

---

## 💰 Monetization (SaaS Model)

### Pricing Tiers
- **Starter:** 1 location, 100 cards, basic reporting
- **Professional:** 5 locations, 1000 cards, advanced analytics
- **Enterprise:** Unlimited, custom integrations, white-label
- **Franchise:** Multi-company, API access, dedicated support

### Add-ons
- Mobile app: $0.50/card/month
- Advanced analytics: $50/location/month
- API access: $100/month
- Custom integrations: Quoted

---

## 🎯 MVP Success Criteria

### Must Have (Phase 1)
- ✅ Secure authentication (MFA for staff+)
- ✅ Multi-level user access
- ✅ Card registration & management
- ✅ Credit transactions (add/deduct/refund)
- ✅ Basic reporting (daily, weekly)
- ✅ Audit logging
- ✅ Private deployment (no public exposure)
- ✅ Backup & restore

### Nice to Have (Phase 1-2)
- ⭐ Mobile app for customers
- ⭐ Email notifications
- ⭐ Analytics dashboard
- ⭐ Machine tracking
- ⭐ Multi-location support

### Phase Out (Not MVP)
- ❌ Public API (security risk)
- ❌ Cloud deployment (local only for MVP)
- ❌ Advanced analytics (later)
- ❌ Maintenance scheduling (later)
- ❌ Franchise features (Phase 5)

---

## 🚦 Next Steps

### Immediate Actions
1. ✅ Shutdown public tunnel (DONE)
2. 📝 Finalize this architecture document
3. 🎨 Design UI/UX wireframes
4. 🔐 Define security requirements
5. 💾 Design database schema in detail
6. 📋 Create development roadmap

### Phase 1 (MVP) - 4-6 weeks
1. Set up secure local environment
2. Implement authentication system
3. Build user management
4. Implement card system
5. Build transaction system
6. Create basic reporting
7. Test with staff

### Phase 2-3 - 8-12 weeks
1. Multi-location support
2. Advanced reporting
3. Mobile app MVP
4. Machine tracking
5. Maintenance scheduling

---

## 📊 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Management Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Web App  │  │ Mobile   │  │ Admin    │  │ Reports  │  │
│  │ (React)  │  │ App      │  │ Panel    │  │ (BI)     │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │         │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
┌───────┴─────────────┴─────────────┴─────────────┴─────────┐
│                   API Gateway (Auth + Rate Limit)        │
└───────────────────────┬───────────────────────────────────┘
                        │
┌───────────────────────┴───────────────────────────────────┐
│              Backend Services (FastAPI)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ User     │  │ Card     │  │ Trans    │  │ Reports  │  │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │         │
│       └─────────────┼─────────────┼─────────────┘         │
│                     │             │                       │
│  ┌──────────────────┴─────────────┴──────────────────┐    │
│  │              PostgreSQL (Database)               │    │
│  └──────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────┴───────────────────────────────────┐
│                   Infrastructure                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Redis    │  │ Queue    │  │ Logs     │  │ Monitor  │  │
│  │ (Cache)  │  │ (Async)  │  │ (ELK)    │  │ (Prom)   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────┴───────────────────────────────────┐
│                   Devices (Hardware)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ RFID     │  │ Kiosk    │  │ Mobile   │  │ Payment  │  │
│  │ Readers  │  │ Stations │  │ App      │  │ Gateway  │  │
│  │ (ESP32)  │  │          │  │          │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## 🔒 Security Checklist

### Before Launch (MVP)
- [ ] All user accounts have strong passwords
- [ ] MFA enabled for Level 3+ users
- [ ] Audit logging enabled for all transactions
- [ ] Database encrypted at rest
- [ ] HTTPS enforced everywhere
- [ ] No public API exposure
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] SQL injection testing
- [ ] XSS prevention
- [ ] Regular backup schedule
- [ ] Backup encryption tested
- [ ] Disaster recovery plan documented
- [ ] Security audit completed

---

## 📞 Support & Maintenance

### Tiered Support
- **Level 1:** FAQ, basic troubleshooting (automated)
- **Level 2:** Technical support (staff)
- **Level 3:** Escalation (senior staff)
- **Level 4:** Critical issues (development team)

### Maintenance Windows
- Weekly: Security updates (low traffic)
- Monthly: Feature updates
- Quarterly: Major version upgrades
- Annual: Security audit & penetration testing

### Uptime SLA
- MVP: 99% uptime
- Professional: 99.5% uptime
- Enterprise: 99.9% uptime

---

## 💬 Your Feedback Needed

**Critical Questions:**
1. **How many locations** do you have now? Planning for?
2. **How many users** at each level (staff, supervisors, etc.)?
3. **What's your timeline** for MVP launch?
4. **Budget constraints** for hosting/infrastructure?
5. **Integration needs** (payment gateways, accounting, etc.)?
6. **Compliance requirements** (financial, data privacy)?
7. **Mobile app priority** - MVP or later?
8. **Customer portal** needed?

**Let's finalize this architecture, then we can build it right the first time!**

---

## 🎯 Summary

**This is NOT a card system** - it's a **business management platform**.

- Start small (MVP card reader)
- Think big (amusement park empire)
- Build secure (from day one)
- Plan ahead (architecture supports growth)
- Ship fast (MVP in 4-6 weeks)
- Scale up (phased expansion)

**One system. Unlimited possibilities.** 🚀