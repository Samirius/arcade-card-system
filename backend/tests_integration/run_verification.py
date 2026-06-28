"""
End-to-end functional verification harness.
Runs the real FastAPI app against a real PostgreSQL and drives every critical
flow, recording hard PASS/FAIL + evidence. Run with PYTHONPATH=backend.
"""
import os, sys, traceback, uuid

os.environ.setdefault("SECRET_KEY", "verification_secret_key_0123456789_abcdef")
os.environ.setdefault("DATABASE_URL", "postgresql://arcade_user:arcade_password@localhost:5433/arcade_management")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")

from sqlalchemy import text, inspect
from app.database import Base, engine, SessionLocal
import app.models               # 9 core tables
import app.models.balance       # register ledger tables (app does NOT do this)
import app.models.offline       # register offline tables (app does NOT do this)
from app.utils.jwt import decode_token
from app.utils.email_verification import create_email_verification_token
import pyotp

# ---- reset schema & create everything we can ----
with engine.begin() as c:
    c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from app.main import app

API = "/api/v1"
PW = "VerifyPass123!"
results = []
def rec(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
def jget(r, *keys):
    try:
        d = r.json()
        for k in keys: d = d[k]
        return d
    except Exception:
        return None

def reg(c, email, role="STAFF"):
    return c.post(f"{API}/auth/register", json={"email": email, "password": PW,
                  "first_name": "T", "last_name": "U", "role": role})
def verify(c, email):
    tok = create_email_verification_token(email)
    return c.post(f"{API}/auth/verify-email/{tok}")
def login(c, email, password=PW):
    return c.post(f"{API}/auth/login", json={"email": email, "password": password})
def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}

with TestClient(app, raise_server_exceptions=False) as c:
    # route sanity
    paths = sorted({r.path for r in app.routes})
    print("ROUTES:", [p for p in paths if p.startswith('/api')][:40])

    # 1. register STAFF
    e1 = f"staff_{uuid.uuid4().hex[:8]}@t.co"
    r = reg(c, e1, "STAFF")
    rec("register STAFF -> 201", r.status_code == 201, f"{r.status_code} {r.text[:120]}")

    # 2. H2 role-escalation probe: self-register as OWNER
    eo = f"owner_{uuid.uuid4().hex[:8]}@t.co"
    r = reg(c, eo, "OWNER")
    got_owner = r.status_code == 201 and str(r.json().get("status"))
    # check stored role
    s = SessionLocal(); from app.models.user import User
    urow = s.query(User).filter(User.email == eo).first()
    role_stored = urow.role if urow else None
    s.close()
    rec("H2: self-register as OWNER is REJECTED", not (r.status_code == 201 and str(role_stored).endswith("OWNER")),
        f"status={r.status_code}, stored_role={role_stored} (expected escalation BLOCKED)")

    # 3. C1: email verification activates + login works
    r = verify(c, e1)
    rec("C1: verify-email activates account", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    r = login(c, e1)
    ok_login = r.status_code == 200
    rec("login STAFF after verify -> 200", ok_login, f"{r.status_code} {r.text[:120]}")
    access = refresh = None
    if ok_login:
        access = jget(r,"access_token"); refresh = jget(r,"refresh_token")
        pl = decode_token(access)
        rec("access token carries token_version (H1 mechanism)", pl and "token_version" in pl, f"claims={list(pl.keys()) if pl else None}")

    # 4. H4: failed-login lockout has no TypeError, locks after 5
    el = f"lock_{uuid.uuid4().hex[:8]}@t.co"; reg(c, el, "STAFF"); verify(c, el)
    codes = []
    for i in range(5):
        rr = login(c, el, "WrongPass999!"); codes.append(rr.status_code)
    r6 = login(c, el, "WrongPass999!")
    no_500 = all(x == 401 for x in codes) and r6.status_code == 401
    locked = "lock" in r6.text.lower()
    rec("H4: 5 bad logins lock account, no 500/TypeError", no_500 and locked, f"codes={codes}, 6th={r6.status_code}:{r6.text[:60]}")

    # 5. C2: MFA setup works (no NameError) + full MFA login
    if access:
        r = c.post(f"{API}/auth/mfa/setup/initiate", headers=hdr(access))
        rec("C2: MFA initiate -> 200 (no NameError)", r.status_code == 200, f"{r.status_code} {r.text[:80]}")
        s = SessionLocal(); urow = s.query(User).filter(User.email == e1).first(); secret = urow.mfa_secret; s.close()
        if r.status_code == 200 and secret:
            code = pyotp.TOTP(secret).now()
            rv = c.post(f"{API}/auth/mfa/setup/verify", headers=hdr(access), json={"mfa_code": code})
            rec("C2: MFA verify/enable -> 200", rv.status_code == 200, f"{rv.status_code} {rv.text[:80]}")
            code2 = pyotp.TOTP(secret).now()
            rm = c.post(f"{API}/auth/login/mfa", json={"email": e1, "password": PW, "mfa_code": code2})
            rec("MFA login (/login/mfa) -> 200", rm.status_code == 200, f"{rm.status_code} {rm.text[:80]}")

    # 6. Privileged login deadlock: ADMIN needs MFA to login but can't set up MFA without login
    ea = f"admin_{uuid.uuid4().hex[:8]}@t.co"; reg(c, ea, "ADMIN"); verify(c, ea)
    ra = login(c, ea)
    rec("ADMIN can log in (privileged-MFA deadlock check)", ra.status_code == 200,
        f"{ra.status_code}:{ra.text[:90]} (FAIL => privileged accounts cannot authenticate)")

    # 7. NEW-1: logout without refresh_token body
    e7 = f"lo_{uuid.uuid4().hex[:8]}@t.co"; reg(c, e7, "STAFF"); verify(c, e7)
    lr = login(c, e7); a7 = jget(lr,"access_token"); rt7 = jget(lr,"refresh_token")
    lo_nobody = c.post(f"{API}/auth/logout", headers=hdr(a7))
    rec("NEW-1: logout w/o refresh_token body does NOT 500", lo_nobody.status_code != 500,
        f"status={lo_nobody.status_code} (500 => undefined 'request' bug)")

    # 8. H1: revocation. fresh login, logout WITH refresh token, then reuse tokens
    e8 = f"rev_{uuid.uuid4().hex[:8]}@t.co"; reg(c, e8, "STAFF"); verify(c, e8)
    lr = login(c, e8); a8 = jget(lr,"access_token"); rt8 = jget(lr,"refresh_token")
    lo = c.post(f"{API}/auth/logout", headers=hdr(a8), json={"refresh_token": rt8})
    me_after = c.get(f"{API}/auth/me", headers=hdr(a8))
    rec("H1: old ACCESS token rejected after logout", me_after.status_code == 401, f"/me -> {me_after.status_code}")
    rf = c.post(f"{API}/auth/refresh", json={"refresh_token": rt8})
    rec("H1: old REFRESH token rejected after logout", rf.status_code != 200,
        f"/refresh -> {rf.status_code} (200 => refresh bypasses revocation)")

    # ---- MONEY (STAFF can create/add/charge) ----
    staff_login = login(c, e1)  # e1 now has MFA -> login plain should fail
    # use a fresh non-MFA staff for money
    em = f"money_{uuid.uuid4().hex[:8]}@t.co"; reg(c, em, "STAFF"); verify(c, em)
    am = jget(login(c, em),"access_token")
    cuid = f"CARD{uuid.uuid4().hex[:8].upper()}"
    rc_ = c.post(f"{API}/cards/", headers=hdr(am), json={"card_uid": cuid, "owner": "Tester", "card_type": "REGULAR", "initial_balance": 0})
    rec("create card -> 201", rc_.status_code == 201, f"{rc_.status_code} {rc_.text[:100]}")
    ra_ = c.post(f"{API}/cards/{cuid}/add-credit", headers=hdr(am), json={"amount": 100, "notes": "load"})
    bal_after_add = ra_.json().get("new_balance") if ra_.status_code == 200 else None
    rec("add-credit 100 -> balance 100", str(bal_after_add) in ("100.00", "100"), f"{ra_.status_code} new_balance={bal_after_add}")
    rch = c.post(f"{API}/cards/{cuid}/charge", headers=hdr(am), json={"amount": 30, "notes": "play"})
    rec("charge 30 -> 200", rch.status_code == 200, f"{rch.status_code} new_balance={rch.json().get('new_balance') if rch.status_code==200 else rch.text[:80]}")
    rover = c.post(f"{API}/cards/{cuid}/charge", headers=hdr(am), json={"amount": 100000, "notes": "over"})
    rec("charge over balance -> 400 rejected", rover.status_code == 400, f"{rover.status_code}")

    # ---- LEDGER (AR-2) ----
    cl = f"LEDG{uuid.uuid4().hex[:8].upper()}"
    c.post(f"{API}/cards/", headers=hdr(am), json={"card_uid": cl, "owner": "Ledger", "card_type": "REGULAR", "initial_balance": 0})
    add_l = c.post(f"{API}/balance/add", headers=hdr(am), json={"card_uid": cl, "amount": 50, "notes": "viaLedger"})
    rec("AR-2: /balance/add works (ledger path)", add_l.status_code in (200, 201), f"{add_l.status_code} {add_l.text[:100]}")
    rec_l = c.get(f"{API}/balance/reconcile/{cl}", headers=hdr(am))
    rec("AR-2: reconcile after ledger op = MATCHED", rec_l.status_code == 200 and rec_l.json().get("status") == "MATCHED",
        f"{rec_l.status_code} {rec_l.text[:120]}")
    # legacy charge bypasses ledger -> discrepancy
    c.post(f"{API}/cards/{cl}/charge", headers=hdr(am), json={"amount": 10, "notes": "legacy"})
    rec_l2 = c.get(f"{API}/balance/reconcile/{cl}", headers=hdr(am))
    st = rec_l2.json().get("status") if rec_l2.status_code == 200 else None
    rec("AR-2 gap: legacy /charge bypasses ledger (=> DISCREPANCY)", st == "DISCREPANCY",
        f"reconcile status={st} (DISCREPANCY confirms legacy endpoints don't write ledger)")

    # ---- TENANT ISOLATION (AR-1) ----
    eb = f"userB_{uuid.uuid4().hex[:8]}@t.co"; reg(c, eb, "STAFF"); verify(c, eb)
    ab = jget(login(c, eb),"access_token")
    cross = c.get(f"{API}/cards/{cuid}", headers=hdr(ab))  # user B reads user A's card
    rec("AR-1: cross-tenant card access is BLOCKED", cross.status_code in (403, 404),
        f"user B GET A's card -> {cross.status_code} (200 => no tenant isolation)")

    # ---- AUDIT PERSISTENCE (BE-6) ----
    s = SessionLocal()
    audit_count = s.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
    s.close()
    rec("BE-6: audit_logs rows persisted", audit_count and audit_count > 0, f"audit_logs count={audit_count}")

# summary
print("\n================ SUMMARY ================")
p = sum(1 for _,ok,_ in results if ok); f = len(results) - p
for name, ok, detail in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"\nTOTAL: {p} PASS / {f} FAIL  of {len(results)}")
sys.exit(1 if f else 0)  # non-zero on any failure -> CI-usable
