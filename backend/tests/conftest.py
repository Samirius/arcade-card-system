"""
Shared pytest fixtures for the backend test suite (BE-6).

Resets the database schema exactly ONCE per test session (mirroring the
proven pattern used by tests_integration/run_verification.py and
tools/reader_sim.py): drop + recreate the ``public`` schema and run
``Base.metadata.create_all`` BEFORE the FastAPI app is imported, so no
partial/stale schema from a previous run leaks into these tests, and so this
suite is self-contained regardless of whether Alembic migrations were run
first.

Provides small helper functions (not fixtures, so they compose freely inside
a test body) to drive the common flows every suite needs:
    * register_user / verify_user / login_user
    * seed_company_and_owner (direct DB seed of a company + ACTIVE OWNER)
    * enroll_device (via the authenticated HTTP API)

Every test gets a fresh ``client`` (function-scoped) wrapping the same
FastAPI app, and a fresh ``db_session`` for direct DB assertions/seeding.
"""
import os
import uuid

# ---------------------------------------------------------------------- #
# Env defaults MUST be set before importing anything from `app.*` so that
# app.config's SECRET_KEY / DATABASE_URL validation succeeds even if the
# caller didn't export them. Matches the pattern used by
# tests_integration/run_verification.py and tools/reader_sim.py.
# ---------------------------------------------------------------------- #
os.environ.setdefault("SECRET_KEY", "verification_secret_key_0123456789_abcdef")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://arcade_user:arcade_password@localhost:5433/arcade_management",
)
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")

import pytest
from sqlalchemy import text

from app.database import Base, engine, SessionLocal
# Import every model module so the FULL metadata is registered before
# create_all runs (app/models/__init__ does not itself import
# app.models.offline; the harness scripts import it explicitly for the
# same reason).
import app.models          # core tables (users, cards, transactions, ...)
import app.models.balance  # ledger tables
import app.models.offline  # offline auth tables


# ---------------------------------------------------------------------- #
# ONE-TIME schema reset, at collection time (module import), before any
# test module's `from app.main import app` executes. This is intentionally
# NOT a fixture: fixtures run after collection, but other test files import
# app.main at module scope, so the reset must happen here, now.
# ---------------------------------------------------------------------- #
with engine.begin() as _conn:
    _conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
Base.metadata.create_all(bind=engine)


from fastapi.testclient import TestClient
from app.main import app

API = "/api/v1"
DEFAULT_PASSWORD = "TestPass123!"


@pytest.fixture(scope="session")
def api_client():
    """Session-wide TestClient. The schema reset above already ran once."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def client(api_client):
    """Per-test alias for the shared client (kept function-scoped for
    readability at call sites; the underlying TestClient/app is reused)."""
    return api_client


@pytest.fixture()
def db_session():
    """A fresh SQLAlchemy session for direct DB setup/assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """
    security_middleware (app/utils/security.py) applies a 100 requests / 60
    second cap keyed by client IP, backed by the process-global in-memory
    ``rate_limiter`` singleton in app.utils.rate_limit. Every TestClient
    request originates from the same synthetic "testclient" IP, and this
    suite legitimately issues well over 100 requests per test file (register
    + verify + login + several follow-up calls per test), so without a reset
    the shared window fills up mid-suite and later tests start getting
    rate-limited -- surfacing as unhandled 500s (an HTTPException raised
    inside `@app.middleware("http")` propagates as an unhandled exception
    rather than a clean 429, per Starlette's BaseHTTPMiddleware semantics).
    Clearing the singleton's bookkeeping before each test keeps every test
    's rate-limit window independent, matching how a real deployment would
    only ever see one client's traffic at a time.
    """
    from app.utils.rate_limit import rate_limiter

    rate_limiter.requests.clear()
    yield
    rate_limiter.requests.clear()


# --------------------------------------------------------------------- #
# Helpers (plain functions, not fixtures — used freely inside test bodies)
# --------------------------------------------------------------------- #
def unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@t.co"


def register_user(client, email: str, password: str = DEFAULT_PASSWORD, role: str = "STAFF"):
    """POST /auth/register. Returns the response object."""
    return client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Test",
            "last_name": "User",
            "role": role,
        },
    )


def verify_user(client, email: str):
    """Activate the account by minting + redeeming a real email-verification token."""
    from app.utils.email_verification import create_email_verification_token

    token = create_email_verification_token(email)
    return client.post(f"{API}/auth/verify-email/{token}")


def login_user(client, email: str, password: str = DEFAULT_PASSWORD):
    """POST /auth/login. Returns the response object (may be 401)."""
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def register_verify_login(client, role: str = "STAFF", password: str = DEFAULT_PASSWORD):
    """Full happy path: register -> verify -> login. Returns (email, access_token, response)."""
    email = unique_email(role.lower())
    r = register_user(client, email, password=password, role=role)
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    rv = verify_user(client, email)
    assert rv.status_code == 200, f"verify failed: {rv.status_code} {rv.text}"
    rl = login_user(client, email, password=password)
    assert rl.status_code == 200, f"login failed: {rl.status_code} {rl.text}"
    return email, rl.json()["access_token"], rl


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def seed_company_and_owner(db_session, password: str = DEFAULT_PASSWORD):
    """
    Directly seed a Company + an ACTIVE, verified OWNER bound to it (no MFA),
    mirroring tools/reader_sim.py's seed_owner_and_company. Useful whenever a
    test needs a user with a REAL company_id (e.g. device enrollment requires
    the caller be bound to a company) without going through the self-register
    flow (which never assigns a company_id).

    Returns (email, password, company_id).
    """
    from app.models.company import Company
    from app.models.user import User, UserRole, UserStatus
    from app.utils.password import hash_password

    suffix = uuid.uuid4().hex[:8]
    company = Company(
        name=f"Test Co {suffix}",
        slug=f"test-co-{suffix}",
        email=f"ops_{suffix}@testco.example",
        status="ACTIVE",
        is_active=True,
        plan="PRO",
        max_venues=5,
        max_users=50,
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    email = f"owner_{suffix}@testco.example"
    owner = User(
        email=email,
        password_hash=hash_password(password),
        first_name="Test",
        last_name="Owner",
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        is_verified=True,
        company_id=company.id,
    )
    db_session.add(owner)
    db_session.commit()

    return email, password, company.id


def enroll_device(client, owner_access_token: str, label: str = "Test Reader"):
    """POST /devices/enroll as an authenticated ADMIN/OWNER. Returns the response object."""
    return client.post(
        f"{API}/devices/enroll",
        headers=auth_headers(owner_access_token),
        json={"label": label, "venue": "Test Venue"},
    )


def create_card(client, access_token: str, card_uid: str = None, owner: str = "Test Owner", initial_balance=0):
    """POST /cards/. Returns the response object."""
    if card_uid is None:
        card_uid = f"CARD{uuid.uuid4().hex[:10].upper()}"
    return client.post(
        f"{API}/cards/",
        headers=auth_headers(access_token),
        json={
            "card_uid": card_uid,
            "owner": owner,
            "card_type": "REGULAR",
            # Coerce to str: httpx's json= kwarg uses stdlib json.dumps()
            # internally, which cannot serialize decimal.Decimal directly.
            # FastAPI/Pydantic coerces the string back to Decimal on receipt.
            "initial_balance": str(initial_balance),
        },
    )
