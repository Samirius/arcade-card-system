# Arcade Management System - DIY Implementation Plan

## 🎯 Project Approach

**Philosophy:** Build it right, step by step, no shortcuts, no rushing.

**Goal:** Production-ready MVP that scales from local VPS to cloud.

**Timeline:** Depends on your schedule - quality over speed.

---

## 📅 Realistic DIY Timeline

### Phase 0: Setup & Foundation (3-5 days)

#### Day 1: Environment Setup
- [ ] Clean up current project (remove insecure code)
- [ ] Set up proper project structure
- [ ] Configure Python virtual environment
- [ ] Set up PostgreSQL with proper permissions
- [ ] Create database schema (from DATABASE_SCHEMA.md)
- [ ] Test database connections
- [ ] Set up version control (Git branches)

#### Day 2: Security Foundation
- [ ] Implement password hashing (bcrypt)
- [ ] Create JWT token system
- [ ] Set up MFA library (pyotp)
- [ ] Create audit logging system
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Create security middleware

#### Day 3: Project Structure
- [ ] Create FastAPI application structure
- [ ] Set up SQLAlchemy models
- [ ] Create Pydantic schemas
- [ ] Set up dependency injection
- [ ] Create error handlers
- [ ] Set up logging
- [ ] Create configuration management

#### Day 4: Testing Setup
- [ ] Set up pytest
- [ ] Create test database
- [ ] Write first unit tests (password hashing)
- [ ] Set up test coverage reporting
- [ ] Create CI/CD structure (local)

#### Day 5: Documentation
- [ ] Update README with setup instructions
- [ ] Create API documentation structure
- [ ] Write deployment guide
- [ ] Create backup/restore procedures

---

### Phase 1: Authentication System (1-2 weeks)

#### Sprint 1: User Registration (3-4 days)
- [ ] Create User model
- [ ] Implement password hashing/validation
- [ ] Create registration endpoint
- [ ] Add email verification (optional for MVP)
- [ ] Create password reset flow
- [ ] Write tests for registration
- [ ] Document API endpoints

**Code Structure:**
```
backend/
├── models/
│   └── user.py              # User model
├── schemas/
│   └── user.py              # User request/response schemas
├── crud/
│   └── user.py              # User database operations
├── api/
│   └── v1/
│       ├── endpoints/
│       │   ├── auth.py      # Registration, login, logout
│       │   └── users.py     # User management
│       └── dependencies.py   # Auth dependencies
└── services/
    └── auth.py              # Auth business logic (JWT, MFA)
```

#### Sprint 2: Login & JWT (2-3 days)
- [ ] Implement login endpoint
- [ ] Create JWT token generation
- [ ] Set up token refresh mechanism
- [ ] Create logout endpoint
- [ ] Implement session management
- [ ] Add login attempt tracking
- [ ] Write tests for login flow

#### Sprint 3: MFA Integration (2-3 days)
- [ ] Add MFA to User model
- [ ] Integrate TOTP (Google Authenticator)
- [ ] Create MFA setup endpoint
- [ ] Create MFA verification endpoint
- [ ] Add MFA enforcement logic
- [ ] Write tests for MFA

#### Sprint 4: User Management (2-3 days)
- [ ] Create user list endpoint (admin only)
- [ ] Create user detail endpoint
- [ ] Implement user update (admin only)
- [ ] Create user deletion (soft delete)
- [ ] Add user status management
- [ ] Write tests for user CRUD

**Deliverable:** Complete, tested authentication system with MFA.

---

### Phase 2: Card Management System (1-2 weeks)

#### Sprint 5: Customer Management (2-3 days)
- [ ] Create Customer model
- [ ] Implement customer CRUD
- [ ] Create customer search
- [ ] Add customer validation
- [ ] Write tests

#### Sprint 6: Card Registration (2-3 days)
- [ ] Create Card model
- [ ] Implement card UID hashing/tokenization
- [ ] Create card registration endpoint
- [ ] Add card validation
- [ ] Implement card types (VIP, Regular, Staff)
- [ ] Write tests

#### Sprint 7: Card Operations (2-3 days)
- [ ] Create card search endpoint
- [ ] Implement card details endpoint
- [ ] Add card status management
- [ ] Create card update endpoint
- [ ] Implement card blocking
- [ ] Write tests

#### Sprint 8: Card Security (2-3 days)
- [ ] Add card activity logging
- [ ] Implement duplicate detection
- [ ] Add unauthorized access alerts
- [ ] Create card audit reports
- [ ] Write security tests

**Deliverable:** Complete card management system with security.

---

### Phase 3: Transaction System (1-2 weeks)

#### Sprint 9: Transaction Models (2-3 days)
- [ ] Create Transaction model
- [ ] Implement transaction types (ADD, DEDUCT, REFUND)
- [ ] Add balance validation
- [ ] Create transaction audit logging
- [ ] Write tests

#### Sprint 10: Credit Operations (2-3 days)
- [ ] Create add credits endpoint
- [ ] Create deduct credits endpoint
- [ ] Implement balance checks
- [ ] Add transaction queue (for offline mode)
- [ ] Write tests

#### Sprint 11: Refund System (2-3 days)
- [ ] Create refund endpoint
- [ ] Implement supervisor approval
- [ ] Add refund limits
- [ ] Create reversal transaction
- [ ] Write tests

#### Sprint 12: Transaction History (2-3 days)
- [ ] Create transaction list endpoint
- [ ] Add filtering (date, type, user)
- [ ] Implement export (CSV/PDF)
- [ ] Create transaction details
- [ ] Write tests

**Deliverable:** Complete transaction system with audit trail.

---

### Phase 4: Reporting & Analytics (1 week)

#### Sprint 13: Basic Reports (2-3 days)
- [ ] Create daily revenue report
- [ ] Create weekly/monthly reports
- [ ] Implement transaction summary
- [ ] Add staff performance report
- [ ] Write tests

#### Sprint 14: Dashboard (2-3 days)
- [ ] Create real-time dashboard
- [ ] Add card statistics
- [ ] Add transaction statistics
- [ ] Implement active user tracking
- [ ] Write tests

#### Sprint 15: Export System (2-3 days)
- [ ] Implement CSV export
- [ ] Add PDF generation
- [ ] Create report scheduling
- [ ] Write tests

**Deliverable:** Complete reporting system.

---

### Phase 5: Device Integration (1-2 weeks)

#### Sprint 16: ESP32 Authentication (2-3 days)
- [ ] Create device certificate system
- [ ] Implement device registration
- [ ] Add device validation
- [ ] Create device management endpoints
- [ ] Write tests

#### Sprint 17: ESP32 API Client (3-4 days)
- [ ] Create API client library for ESP32
- [ ] Implement offline mode (queue)
- [ ] Add auto-sync logic
- [ ] Create firmware update mechanism
- [ ] Write ESP32 tests

#### Sprint 18: Kiosk Integration (2-3 days)
- [ ] Create kiosk mode endpoints
- [ ] Implement self-service card registration
- [ ] Add balance check endpoints
- [ ] Create receipt generation
- [ ] Write tests

**Deliverable:** Complete device integration.

---

### Phase 6: Security Hardening (1 week)

#### Sprint 19: Security Audit (2-3 days)
- [ ] Review all endpoints for vulnerabilities
- [ ] Test for SQL injection
- [ ] Test for XSS
- [ ] Test for CSRF
- [ ] Test rate limiting
- [ ] Test MFA bypass attempts

#### Sprint 20: Performance Testing (2-3 days)
- [ ] Load test API endpoints
- [ ] Test database queries
- [ ] Optimize slow queries
- [ ] Add database indexes
- [ ] Test with 100 concurrent users

#### Sprint 21: Backup & Recovery (2-3 days)
- [ ] Set up automated backups
- [ ] Test backup restore
- [ ] Create disaster recovery plan
- [ ] Document backup procedures
- [ ] Write restore tests

**Deliverable:** Security-hardened, production-ready system.

---

## 🗂️ Project Structure

```
arcade-management-system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app
│   │   ├── config.py                  # Configuration
│   │   ├── database.py                # Database connection
│   │   ├── security.py                # Security utilities
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── customer.py
│   │   │   ├── card.py
│   │   │   ├── transaction.py
│   │   │   ├── location.py
│   │   │   └── machine.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── customer.py
│   │   │   ├── card.py
│   │   │   └── transaction.py
│   │   ├── crud/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── customer.py
│   │   │   ├── card.py
│   │   │   └── transaction.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # Dependencies
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── cards.py
│   │   │       └── transactions.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # JWT, MFA logic
│   │   │   ├── email.py               # Email notifications
│   │   │   └── audit.py               # Audit logging
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── password.py            # Password hashing
│   │       ├── jwt.py                 # JWT utilities
│   │       └── validation.py          # Input validation
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Pytest fixtures
│   │   ├── test_auth.py
│   │   ├── test_cards.py
│   │   ├── test_transactions.py
│   │   └── test_security.py
│   ├── alembic/
│   │   └── versions/                  # Database migrations
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── README.md
├── esp32-firmware/
│   ├── src/
│   │   ├── main.cpp
│   │   ├── api_client.cpp
│   │   └── offline_queue.cpp
│   ├── platformio.ini
│   └── README.md
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── SECURITY.md
├── scripts/
│   ├── backup.sh
│   ├── restore.sh
│   └── migrate.sh
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 🔒 Security Best Practices (Built In)

### 1. Password Security
```python
# Use bcrypt with cost factor 12
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

### 2. JWT Security
```python
# Short-lived access tokens (30 min)
# Refresh tokens (7 days)
# Algorithm: RS256 (asymmetric keys)

access_token = create_access_token(
    data={"sub": user_id, "role": user_role},
    expires_delta=timedelta(minutes=30)
)
```

### 3. MFA Enforcement
```python
# Level 3+ must have MFA
if user.role in ['SUPERVISOR', 'REGIONAL_MGR', 'ADMIN', 'OWNER']:
    if not user.mfa_enabled:
        raise HTTPException(status_code=403, detail="MFA required")
```

### 4. Audit Logging
```python
# Log every critical action
@audit_log
async def create_card(card: CardCreate, db: Session):
    # ... create card ...
    # Automatically logged
```

### 5. Rate Limiting
```python
# 100 requests per minute per user
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/cards/")
@limiter.limit("30/minute")
async def create_card(...):
    # ...
```

---

## 🧪 Testing Strategy

### Unit Tests (per module)
```python
# tests/test_auth.py
def test_password_hashing():
    password = "SecurePass123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("WrongPass", hashed)

def test_jwt_creation():
    token = create_access_token(data={"sub": "user123"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user123"
```

### Integration Tests (end-to-end)
```python
# tests/test_integration.py
async def test_card_registration_flow(client):
    # Register user
    response = await client.post("/api/auth/register", json={...})
    assert response.status_code == 201

    # Login
    response = await client.post("/api/auth/login", json={...})
    token = response.json()["access_token"]

    # Create card
    response = await client.post(
        "/api/cards/",
        json={"uid": "TEST123", "owner": "John"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
```

### Security Tests
```python
# tests/test_security.py
def test_sql_injection_prevention(client):
    malicious_input = "'; DROP TABLE users; --"
    response = client.post("/api/auth/register", json={"email": malicious_input})
    assert response.status_code == 400  # Validation error

def test_rate_limiting(client):
    for _ in range(101):
        response = client.post("/api/auth/login", json={...})
    assert response.status_code == 429  # Too many requests
```

---

## 📊 Quality Gates

### Before Moving to Next Phase:

**Security Checklist:**
- [ ] All passwords hashed
- [ ] No SQL injection vulnerabilities
- [ ] All endpoints rate-limited
- [ ] XSS prevention enabled
- [ ] CSRF protection (if needed)
- [ ] Audit logging on all financial transactions

**Code Quality Checklist:**
- [ ] All unit tests passing
- [ ] Test coverage > 80%
- [ ] No linting errors
- [ ] Code reviewed (self or peer)
- [ ] Documentation updated

**Performance Checklist:**
- [ ] API response time < 500ms (P95)
- [ ] Database queries optimized
- [ ] No memory leaks
- [ ] Can handle 100 concurrent users

**Documentation Checklist:**
- [ ] API endpoints documented
- [ ] Database schema documented
- [ ] Setup instructions clear
- [ ] Deployment guide complete

---

## 🚀 Deployment Strategy

### Local VPS (MVP)
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/arcade
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    depends_on:
      - db

  db:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=arcade_user
      - POSTGRES_PASSWORD=***DATABASE=arcade

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Cloud Migration (Phase 2+)
- Containerized application (Docker)
- Environment variables for config
- No hardcoded paths/URLs
- Database migration scripts (Alembic)
- Stateless design (can scale horizontally)

---

## 📋 Daily Work Routine

### When You Sit Down to Code:

1. **Pull latest changes**
   ```bash
   git pull origin main
   ```

2. **Run tests**
   ```bash
   pytest backend/tests/ -v
   ```

3. **Create feature branch**
   ```bash
   git checkout -b feature/authentication
   ```

4. **Work on ONE thing**
   - Don't skip ahead
   - Follow the sprint checklist
   - Write tests BEFORE code (TDD)

5. **Commit frequently**
   ```bash
   git add .
   git commit -m "feat: implement user registration"
   ```

6. **Run tests again**
   ```bash
   pytest backend/tests/ -v
   ```

7. **Push and merge**
   ```bash
   git push origin feature/authentication
   # Create PR, review, merge
   ```

---

## 🎯 Success Metrics

### Phase 1 (Authentication):
- ✅ Can register, login, logout
- ✅ JWT tokens work correctly
- ✅ MFA can be enabled/verified
- ✅ Failed login attempts tracked
- ✅ All tests passing
- ✅ Zero security vulnerabilities

### Phase 2 (Cards):
- ✅ Can register cards
- ✅ Card UIDs are hashed
- ✅ Card search works
- ✅ Card blocking works
- ✅ All tests passing
- ✅ Audit logs created

### Phase 3 (Transactions):
- ✅ Can add/deduct credits
- ✅ Balance validation works
- ✅ Refunds require approval
- ✅ All transactions logged
- ✅ All tests passing
- ✅ Financial audit trail complete

### Final MVP:
- ✅ All phases complete
- ✅ All tests passing
- ✅ Security audit passed
- ✅ Performance tests passed
- ✅ Documentation complete
- ✅ Ready for production use

---

## 💡 Tips for DIY Development

### 1. Don't Skip Tests
**Tests catch bugs early.** Writing tests first saves time debugging later.

### 2. Small Commits
**Commit often.** Each commit should be one logical change.

### 3. Read Documentation
**Don't guess.** Read the docs for FastAPI, SQLAlchemy, PostgreSQL.

### 4. Security First
**Never skip security.** Every endpoint must be secure from day one.

### 5. Take Breaks
**Quality over speed.** If you're tired, stop. Rushing creates bugs.

### 6. Version Control
**Use branches.** Never work directly on main.

### 7. Document as You Go
**Write docs with code.** Don't leave documentation for later.

---

## 📞 When to Ask for Help

**Good times to reach out:**
- Stuck on a bug for > 1 hour
- Unsure about security implementation
- Architecture question
- Performance issue
- Need code review

**Before asking:**
- Check error messages
- Google the error
- Read relevant documentation
- Try a minimal reproduction

---

## 🎬 Next Step: Phase 0, Day 1

**We start with environment setup.**

Tasks:
1. Clean up current insecure code
2. Set up proper project structure
3. Configure database
4. Test everything works

**Ready to begin?** Just say **"Start Phase 0"** and I'll guide you through Day 1 step by step!

---

**This is your system. Build it right.** 🚀