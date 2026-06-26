# Arcade Card System - Backlog & Technical Debt

## 🔴 Blockers (Must Fix Before Production)

None - Phase 0 approved for Phase 1.

---

## 🟡 Non-Blocking Issues (Track & Fix Later)

### 1. Pydantic Deprecation Warnings
- **File:** `backend/app/schemas/user.py`, `card.py`, `transaction.py`
- **Issue:** Using deprecated `class Config:` syntax
- **Warning:** `PydanticDeprecatedSince20: Support for class-based 'config' is deprecated, use ConfigDict instead`
- **Impact:** Will break in Pydantic v3.0
- **Priority:** Medium
- **Target Fix:** Phase 2
- **Status:** ⏳ Not Started

**Fix Required:**
```python
# BEFORE (deprecated)
class UserResponse(BaseModel):
    class Config:
        from_attributes = True

# AFTER (new syntax)
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

---

### 2. Missing Environment Variable Example
- **Issue:** No `.env.example` file for new developers
- **Impact:** Hard for new devs to get started
- **Priority:** Low
- **Target Fix:** Phase 1 end
- **Status:** ⏳ Not Started

**Required:** Create `backend/.env.example` with all required variables

---

## 🔵 Future Tasks (Phase 2+)

### 1. Complete Authorization Implementation
- **File:** `backend/app/utils/security.py`
- **Issue:** `require_role()` is a stub
- **Status:** ⏳ Phase 1
- **Description:** Fetch user from database, check role, enforce permissions

### 2. Enforce MFA
- **File:** `backend/app/utils/security.py`
- **Issue:** `require_mfa()` is a no-op
- **Status:** ⏳ Phase 1
- **Description:** Check user MFA status, require for privileged roles

### 3. Add Endpoint-Specific Rate Limits
- **Issue:** Only global rate limit (100 req/min)
- **Status:** ⏳ Phase 1
- **Required:**
  - Login: 10 req/min
  - Password reset: 5 req/min
  - Card operations: 50 req/min
  - Admin endpoints: 20 req/min

### 4. Add Request/Response Logging with IDs
- **Issue:** No request ID generation
- **Status:** ⏳ Phase 1
- **Description:**
  - Generate unique request ID
  - Log request ID, method, path, user_id, duration, status_code
  - Use request ID for tracing

### 5. Improve Error Handling
- **Issue:** Generic error responses
- **Status:** ⏳ Phase 1
- **Description:**
  - Request ID in error responses
  - Error classification (internal vs user-facing)
  - Better error messages

### 6. Database Migrations with Alembic
- **Issue:** Alembic configured but not used
- **Status:** ⏳ Phase 1
- **Description:**
  - Create initial migration
  - Set up migration workflow
  - Add rollback strategy

### 7. Test Coverage to 90%+
- **Current:** 62%
- **Target:** 90%
- **Status:** ⏳ Phase 1 end
- **Priority:** High

### 8. API Documentation Version Control
- **Issue:** Documentation always enabled
- **Status:** ⏳ Phase 2
- **Description:**
  - Disable docs in production
  - Version the API docs

### 9. Response Time Tracking
- **Issue:** No performance monitoring
- **Status:** ⏳ Phase 2
- **Description:**
  - Track response times
  - Log slow requests (>2s)
  - Performance metrics

### 10. User-Agent Validation
- **Issue:** No UA header validation
- **Status:** ⏳ Phase 2
- **Description:**
  - Validate User-Agent header
  - Help block bot traffic

---

## 📚 Documentation Tasks

### 1. Deployment Guide (Create Later)
- **File:** `DEPLOYMENT.md`
- **Status:** ⏳ Save for later
- **Required Sections:**
  - Production environment setup
  - Database configuration
  - SSL/TLS setup
  - Environment variables
  - Reverse proxy (Nginx)
  - Systemd service setup
  - Monitoring setup
  - Backup strategy
  - Rollback procedure

### 2. API Documentation
- **File:** `API.md`
- **Status:** ⏳ Phase 2
- **Required Sections:**
  - All endpoints
  - Request/response schemas
  - Authentication methods
  - Rate limits
  - Error codes

### 3. Developer Guide
- **File:** `DEVELOPER.md`
- **Status:** ⏳ Phase 2
- **Required Sections:**
  - Local development setup
  - Testing guide
  - Code style
  - Git workflow
  - Architecture overview

---

## 🔧 Technical Improvements

### 1. Redis Rate Limiting (Phase 2)
- **Current:** In-memory (doesn't scale, lost on restart)
- **Target:** Redis-based rate limiting
- **Benefits:**
  - Persistent across restarts
  - Scales across multiple servers
  - Better performance

### 2. Distributed Tracing (Phase 2)
- **Current:** Basic logging
- **Target:** OpenTelemetry + Jaeger
- **Benefits:**
  - Full request tracing
  - Performance insights
  - Debug distributed issues

### 3. Structured Logging (Phase 2)
- **Current:** Print statements
- **Target:** Structured JSON logs
- **Benefits:**
  - Better log parsing
  - Log aggregation
  - Easier debugging

### 4. Request Size Limits (Phase 1)
- **Issue:** No limits on JSON body, URL length
- **Required:**
  - Max JSON body: 10MB
  - Max URL length: 2000 chars
  - Max query params: 100

---

## 🏗️ Architecture Improvements

### 1. Caching Layer (Phase 2)
- **Target:** Redis cache for:
  - User sessions
  - Card balances
  - Rate limits
  - Frequently accessed data

### 2. Message Queue (Phase 2)
- **Target:** Celery + Redis for:
  - Audit logging (async)
  - Email notifications
  - Background jobs
  - Scheduled tasks

### 3. Read Replicas (Phase 3)
- **Target:** Read replicas for:
  - Analytics queries
  - Reporting
  - Dashboard data

---

## 📊 Monitoring & Observability

### 1. Health Checks (Phase 1)
- **Current:** Basic health check
- **Required:**
  - Database connection status
  - Redis connection status
  - Cache hit rate
  - Service version
  - Uptime
  - Memory usage

### 2. Metrics Collection (Phase 2)
- **Target:** Prometheus + Grafana
- **Metrics:**
  - Request rate
  - Response times
  - Error rates
  - Database query times
  - Cache hit rates

### 3. Alerting (Phase 2)
- **Target:** Alertmanager + PagerDuty
- **Alerts:**
  - High error rates
  - Slow response times
  - Database connection failures
  - Memory exhaustion
  - Disk space low

---

## 🔐 Security Enhancements (Phase 2+)

### 1. Web Application Firewall (WAF)
- **Target:** ModSecurity or Cloudflare WAF
- **Protection:**
  - SQL injection
  - XSS
  - CSRF
  - LFI
  - RFI

### 2. DDoS Protection
- **Target:** Cloudflare or AWS Shield
- **Features:**
  - Rate limiting
  - IP blocking
  - Challenge pages
  - Bot detection

### 3. Secret Scanning
- **Target:** GitGuardian or TruffleHog
- **Purpose:** Scan for leaked secrets in git history

### 4. Security Headers Scanning
- **Target:** Security Headers or Mozilla Observatory
- **Purpose:** Ensure all security headers are present

---

## 📱 Frontend Tasks (Phase 3+)

### 1. Web Dashboard
- **Status:** Not Started
- **Tech Stack:** React/Vue + TypeScript
- **Features:**
  - User management
  - Card management
  - Transaction history
  - Analytics dashboard
  - Reports

### 2. Mobile App
- **Status:** Not Started
- **Tech Stack:** React Native or Flutter
- **Features:**
  - Staff mobile app
  - QR code scanning
  - Offline mode
  - Push notifications

---

## 🧪 Testing Improvements

### 1. Integration Tests (Phase 1)
- **Current:** Unit tests only
- **Required:**
  - End-to-end API tests
  - Database integration tests
  - Security tests (OWASP ZAP)

### 2. Performance Tests (Phase 2)
- **Target:** Locust or k6
- **Tests:**
  - Load testing (1000+ concurrent users)
  - Stress testing (peak load)
  - Endurance testing (24 hours)

### 3. Security Tests (Phase 2)
- **Target:** OWASP ZAP + Burp Suite
- **Tests:**
  - SQL injection
  - XSS
  - CSRF
  - Authentication bypass
  - Authorization bypass

---

## 📦 Deployment Tasks

### 1. CI/CD Pipeline (Phase 2)
- **Target:** GitHub Actions
- **Stages:**
  - Lint
  - Test
  - Build
  - Security scan
  - Deploy to staging
  - Deploy to production

### 2. Containerization (Phase 2)
- **Target:** Docker
- **Files:**
  - `Dockerfile`
  - `docker-compose.yml`
  - `.dockerignore`

### 3. Kubernetes (Phase 3)
- **Target:** K8s deployment
- **Manifests:**
  - Deployment
  - Service
  - ConfigMap
  - Secret
  - Ingress
  - HPA (Horizontal Pod Autoscaler)

---

## 🔄 Maintenance Tasks

### 1. Dependency Updates
- **Frequency:** Weekly
- **Tool:** Dependabot
- **Action:** Create PRs for dependency updates

### 2. Security Scanning
- **Frequency:** Daily
- **Tool:** Snyk or Trivy
- **Action:** Scan for vulnerabilities

### 3. Backup Testing
- **Frequency:** Monthly
- **Action:** Restore from backup and verify

### 4. Log Rotation
- **Frequency:** Automatic
- **Tool:** Logrotate
- **Action:** Rotate and compress old logs

---

## 📈 Performance Optimization

### 1. Database Optimization (Phase 2)
- **Actions:**
  - Add missing indexes
  - Optimize slow queries
  - Connection pooling tuning
  - Query result caching

### 2. API Optimization (Phase 2)
- **Actions:**
  - Response compression (gzip)
  - Pagination for large datasets
  - Field selection (GraphQL-style)
  - Async operations

### 3. Frontend Optimization (Phase 3)
- **Actions:**
  - Code splitting
  - Lazy loading
  - Image optimization
  - CDN for static assets

---

## 📝 Notes

- This file is the single source of truth for all non-blocking issues and future tasks
- Update this file whenever:
  - A new issue is discovered
  - A task is completed
  - A priority changes
- Always check this file before starting new work to avoid duplicating efforts

---

**Last Updated:** June 26, 2026  
**Maintained By:** Samir George  
**Next Review:** End of Phase 1