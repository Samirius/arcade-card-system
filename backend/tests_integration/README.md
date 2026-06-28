# Functional Verification Harness

Proves what is **actually working** end-to-end against a **real PostgreSQL** —
not just that code compiles. Re-run this on every change; it exits non-zero on
any failure, so it works in CI.

## What it checks
- `run_verification.py` — boots the real FastAPI app (TestClient) against Postgres and drives
  every critical flow: register → email-verify → login → MFA enable/login → logout →
  token revocation, card create/add/charge/insufficient, ledger reconcile, the legacy-endpoint
  ledger-bypass, cross-tenant access, and audit persistence. Prints PASS/FAIL per flow.
- `conc_db.py` — fires 20 concurrent charges at one card via independent DB sessions to prove
  the `SELECT ... FOR UPDATE` row lock prevents overdraft (H3).
- `check_migrations.sh` — applies every `migrations/*.sql` to a fresh DB in order and reports
  which apply cleanly (catches the `fix_schema_orm_drift.sql` DROP TYPE failure).

## Prerequisites
- A running PostgreSQL. Easiest: `docker compose up -d postgres` (uses the repo's compose),
  or any local Postgres. Then set:

```bash
export DATABASE_URL="postgresql://USER:PASS@HOST:PORT/DBNAME"
export SECRET_KEY="a-string-at-least-32-characters-long-xxxxx"
export ENVIRONMENT=development
```

- Python deps (NOTE: the repo `requirements.txt` is missing some — install these too):

```bash
pip install -r requirements.txt
pip install email-validator "qrcode[pil]" slowapi   # MISSING from requirements.txt
pip install pytest httpx==0.25.2 requests pyotp     # test tooling (httpx pinned for TestClient)
```

## Run it
```bash
cd backend
PYTHONPATH=. python tests_integration/run_verification.py     # E2E flows (exit!=0 on failure)
PYTHONPATH=. python tests_integration/conc_db.py              # concurrency/overdraft
bash  tests_integration/check_migrations.sh "$DATABASE_URL"   # migration apply check
```

## Known environment notes
- The app's `create_all` only builds 9 of ~13 tables (ledger/offline/company-plan tables are
  not imported in `app/models/__init__.py`). The harness imports `app.models.balance` and
  `app.models.offline` so those tables exist for testing. In a real deploy you must run the SQL
  migrations to get them — there is no Alembic/migration runner.
- Frontend build and ESP32 firmware compile are verified separately (see the Verification Report).
