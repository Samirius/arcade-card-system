#!/usr/bin/env python3
"""Reader simulator for the DEVICE / READER money tier.

Drives the money path end-to-end and prints [PASS]/[FAIL] per step with a final
tally. This is how the orchestrator verifies the feature.

Steps
-----
1. Seed an OWNER (bound to a fresh company), enroll a device, create a card, top up.
2. Online ``/v1/charge`` -> assert approved and balance decremented.
3. Repeat the SAME client_txn_id -> assert idempotent (no double debit).
4. Fetch the offline envelope and VERIFY its Ed25519 signature with the pubkey.
5. Build an offline batch that overspends and call ``/v1/reconcile`` -> assert
   shortfall recorded and balance floored at 0.

Runs IN-PROCESS via FastAPI's TestClient by default (no live server needed):

    PYTHONPATH=. \
    SECRET_KEY=... DATABASE_URL=... ENVIRONMENT=development DEBUG=false \
    python tools/reader_sim.py

Against a live server instead:

    python tools/reader_sim.py --base-url http://localhost:8000

Exit code is non-zero if any step fails (CI-usable).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import uuid
from datetime import datetime, timezone

# Sensible defaults so the script is runnable without pre-exporting env
# (mirrors the verification harness).
os.environ.setdefault("SECRET_KEY", "verification_secret_key_0123456789_abcdef")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://arcade_user:arcade_password@localhost:5433/arcade_management",
)
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")

# Ensure the backend package is importable when run from anywhere.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

API = "/api/v1"
PW = "ReaderSimPass123!"

_results = []


def rec(name, passed, detail=""):
    _results.append((name, bool(passed)))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}" + (f" :: {detail}" if detail else ""))


# --------------------------------------------------------------------------- #
# HTTP client abstraction: in-process TestClient OR live server via requests.
# --------------------------------------------------------------------------- #
class InProcessClient:
    """Thin wrapper over FastAPI TestClient with a uniform interface."""

    def __init__(self):
        from fastapi.testclient import TestClient
        from app.main import app

        self._client = TestClient(app, raise_server_exceptions=False)
        self._client.__enter__()

    def post(self, path, headers=None, json=None):
        return self._client.post(path, headers=headers, json=json)

    def get(self, path, headers=None):
        return self._client.get(path, headers=headers)

    def close(self):
        try:
            self._client.__exit__(None, None, None)
        except Exception:
            pass


class LiveClient:
    """Wrapper over `requests` for a running uvicorn instance."""

    def __init__(self, base_url):
        import requests  # noqa: F401 (imported lazily; only needed for live mode)

        self._requests = requests
        self._base = base_url.rstrip("/")

    def post(self, path, headers=None, json=None):
        return self._requests.post(self._base + path, headers=headers, json=json)

    def get(self, path, headers=None):
        return self._requests.get(self._base + path, headers=headers)

    def close(self):
        pass


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# Seeding (direct DB) — create an OWNER bound to a fresh company.
# --------------------------------------------------------------------------- #
def seed_owner_and_company():
    """Create a company + an active, verified OWNER; return (email, company_id)."""
    from app.database import SessionLocal
    from app.models.company import Company
    from app.models.user import User, UserRole, UserStatus
    from app.utils.password import hash_password

    db = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:8]
        company = Company(
            name=f"ReaderSim Co {suffix}",
            slug=f"readersim-{suffix}",
            email=f"ops_{suffix}@readersim.co",
            status="ACTIVE",
            is_active=True,
            plan="PRO",
            max_venues=5,
            max_users=50,
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        email = f"owner_{suffix}@readersim.co"
        owner = User(
            email=email,
            password_hash=hash_password(PW),
            first_name="Sim",
            last_name="Owner",
            role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            is_verified=True,
            company_id=company.id,
        )
        db.add(owner)
        db.commit()
        return email, company.id
    finally:
        db.close()


def get_card_balance_cents(card_uid):
    """Read a card's balance directly from the DB, in integer cents."""
    from decimal import Decimal
    from app.database import SessionLocal
    from app.models.card import Card

    db = SessionLocal()
    try:
        card = db.query(Card).filter(Card.card_uid == card_uid).first()
        if not card:
            return None
        return int((Decimal(card.balance) * Decimal(100)).to_integral_value())
    finally:
        db.close()


def get_house_shortfall_cents(company_id):
    """Read the company's offline_shortfall house account balance (cents)."""
    from app.database import SessionLocal
    from app.models.device import HouseAccount

    db = SessionLocal()
    try:
        acct = (
            db.query(HouseAccount)
            .filter(
                HouseAccount.company_id == company_id,
                HouseAccount.account_type == "offline_shortfall",
            )
            .first()
        )
        return int(acct.balance_cents) if acct else 0
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Ed25519 verification (independent of the signing util, to truly "verify").
# --------------------------------------------------------------------------- #
def verify_envelope_signature(envelope, public_key_b64):
    """Reconstruct the canonical payload and verify its Ed25519 signature."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    payload = {
        "device_id": envelope["device_id"],
        "offline_cap_cents": envelope["offline_cap_cents"],
        "per_txn_cap_cents": envelope["per_txn_cap_cents"],
        "valid_until": envelope["valid_until"],
        "key_id": envelope["key_id"],
    }
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = base64.b64decode(envelope["signature"])
    pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    try:
        pub.verify(signature, message)
        return True
    except InvalidSignature:
        return False


# --------------------------------------------------------------------------- #
# Main flow
# --------------------------------------------------------------------------- #
def run(client):
    # ---- Step 0: seed owner + company, log in, enroll device, create+topup card
    email, company_id = seed_owner_and_company()

    lr = client.post(f"{API}/auth/login", json={"email": email, "password": PW})
    owner_token = lr.json().get("access_token") if lr.status_code == 200 else None
    rec(
        "seed OWNER + company, owner login -> token",
        lr.status_code == 200 and owner_token,
        f"login status={lr.status_code}",
    )
    if not owner_token:
        return

    # Enroll device
    enr = client.post(
        f"{API}/devices/enroll",
        headers=hdr(owner_token),
        json={"label": "Lane 1 Reader", "venue": "Main Floor"},
    )
    device_token = enr.json().get("device_token") if enr.status_code == 201 else None
    device_id = enr.json().get("id") if enr.status_code == 201 else None
    rec(
        "enroll device -> 201 + one-time device_token",
        enr.status_code == 201 and bool(device_token) and bool(device_id),
        f"status={enr.status_code}",
    )
    if not device_token:
        return

    # Create a card + top it up (owner/staff path). Start at 0, then add credit.
    card_uid = f"SIMCARD{uuid.uuid4().hex[:8].upper()}"
    cc = client.post(
        f"{API}/cards/",
        headers=hdr(owner_token),
        json={"card_uid": card_uid, "owner": "Sim Player", "card_type": "REGULAR", "initial_balance": 0},
    )
    rec("create card -> 201", cc.status_code == 201, f"status={cc.status_code} {cc.text[:80]}")

    topup = client.post(
        f"{API}/cards/{card_uid}/add-credit",
        headers=hdr(owner_token),
        json={"amount": 50, "notes": "reader sim topup"},
    )
    # 50 dollars == 5000 cents
    start_cents = get_card_balance_cents(card_uid)
    rec(
        "top up card to 5000c (50.00)",
        topup.status_code == 200 and start_cents == 5000,
        f"status={topup.status_code} balance_cents={start_cents}",
    )

    dhdr = hdr(device_token)

    # ---- Step 1: online /v1/charge -> approved + balance decremented
    txn1 = str(uuid.uuid4())
    price1 = 1500  # 15.00
    ch = client.post(
        f"{API}/charge",
        headers=dhdr,
        json={
            "card_uid": card_uid,
            "price_cents": price1,
            "sku": "GAME_TOKEN_x10",
            "client_txn_id": txn1,
            "nonce": uuid.uuid4().hex,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    body = ch.json() if ch.status_code == 200 else {}
    after1_cents = get_card_balance_cents(card_uid)
    approved = body.get("result") == "approved"
    balance_ok = body.get("balance_after_cents") == 3500 and after1_cents == 3500
    rec(
        "online charge 1500c -> approved, balance 5000->3500",
        ch.status_code == 200 and approved and balance_ok,
        f"status={ch.status_code} result={body.get('result')} "
        f"balance_after_cents={body.get('balance_after_cents')} db_cents={after1_cents}",
    )
    server_txn_1 = body.get("server_txn_id")

    # ---- Step 2: repeat SAME client_txn_id -> idempotent, no double debit
    ch2 = client.post(
        f"{API}/charge",
        headers=dhdr,
        json={
            "card_uid": card_uid,
            "price_cents": price1,
            "sku": "GAME_TOKEN_x10",
            "client_txn_id": txn1,  # SAME key
            "nonce": uuid.uuid4().hex,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    body2 = ch2.json() if ch2.status_code == 200 else {}
    after2_cents = get_card_balance_cents(card_uid)
    idem_ok = (
        ch2.status_code == 200
        and body2.get("result") == "approved"
        and body2.get("server_txn_id") == server_txn_1  # same server txn
        and body2.get("balance_after_cents") == 3500
        and after2_cents == 3500  # NOT double-debited
    )
    rec(
        "repeat same client_txn_id -> idempotent (no double debit, balance still 3500)",
        idem_ok,
        f"status={ch2.status_code} result={body2.get('result')} "
        f"replay={body2.get('idempotent_replay')} same_server_txn={body2.get('server_txn_id') == server_txn_1} "
        f"db_cents={after2_cents}",
    )

    # ---- Step 3: offline envelope + Ed25519 signature verification
    pk = client.get(f"{API}/devices/offline-pubkey")
    pub_b64 = pk.json().get("public_key_b64") if pk.status_code == 200 else None
    env = client.get(f"{API}/devices/{device_id}/offline-envelope", headers=dhdr)
    envelope = env.json() if env.status_code == 200 else {}
    sig_verified = False
    if pub_b64 and env.status_code == 200 and envelope.get("signature"):
        sig_verified = verify_envelope_signature(envelope, pub_b64)
    # Negative control: tampering must break verification.
    tamper_ok = True
    if sig_verified:
        tampered = dict(envelope)
        tampered["offline_cap_cents"] = envelope["offline_cap_cents"] + 1
        tamper_ok = not verify_envelope_signature(tampered, pub_b64)
    rec(
        "fetch offline envelope + verify Ed25519 signature (and reject tampering)",
        pk.status_code == 200 and env.status_code == 200 and sig_verified and tamper_ok,
        f"pubkey={pk.status_code} env={env.status_code} verified={sig_verified} "
        f"tamper_rejected={tamper_ok} cap={envelope.get('offline_cap_cents')}",
    )

    # ---- Step 4: offline batch that OVERSPENDS -> reconcile, shortfall, floor at 0
    # Card currently at 3500c. Build a batch totalling more than 3500c.
    shortfall_before = get_house_shortfall_cents(company_id)
    batch = [
        {"card_uid": card_uid, "price_cents": 2000, "client_txn_id": str(uuid.uuid4()), "seq": 1,
         "ts": datetime.now(timezone.utc).isoformat()},
        # This second item overspends: only 1500c left after the first, price 4000c.
        {"card_uid": card_uid, "price_cents": 4000, "client_txn_id": str(uuid.uuid4()), "seq": 2,
         "ts": datetime.now(timezone.utc).isoformat()},
    ]
    rc = client.post(
        f"{API}/reconcile",
        headers=dhdr,
        json={"batch": batch, "key_id": "reader-sim-key"},
    )
    rbody = rc.json() if rc.status_code == 200 else {}
    after_recon_cents = get_card_balance_cents(card_uid)
    shortfall_after = get_house_shortfall_cents(company_id)
    delta_shortfall = shortfall_after - shortfall_before
    # First item: 3500 -> 1500 (applied). Second: needs 4000, only 1500 -> floor 0,
    # shortfall = 4000 - 1500 = 2500.
    expected_shortfall = 2500
    recon_ok = (
        rc.status_code == 200
        and len(rbody.get("applied", [])) == 2
        and rbody.get("shortfall_cents") == expected_shortfall
        and delta_shortfall == expected_shortfall
        and after_recon_cents == 0  # card floored at 0
    )
    rec(
        "reconcile overspend batch -> applied=2, shortfall=2500c, card floored at 0",
        recon_ok,
        f"status={rc.status_code} applied={len(rbody.get('applied', []))} "
        f"declined={len(rbody.get('declined', []))} shortfall_resp={rbody.get('shortfall_cents')} "
        f"house_delta={delta_shortfall} card_cents={after_recon_cents}",
    )

    # ---- Step 5 (bonus): reconcile idempotency — replaying the SAME batch is a no-op
    rc2 = client.post(
        f"{API}/reconcile",
        headers=dhdr,
        json={"batch": batch, "key_id": "reader-sim-key"},
    )
    rbody2 = rc2.json() if rc2.status_code == 200 else {}
    after_recon2_cents = get_card_balance_cents(card_uid)
    shortfall_after2 = get_house_shortfall_cents(company_id)
    replay_ok = (
        rc2.status_code == 200
        and rbody2.get("shortfall_cents") == 0  # no NEW shortfall on replay
        and shortfall_after2 == shortfall_after  # house account unchanged
        and after_recon2_cents == 0  # card unchanged
    )
    rec(
        "reconcile replay is idempotent (no new debit / no new shortfall)",
        replay_ok,
        f"status={rc2.status_code} new_shortfall={rbody2.get('shortfall_cents')} "
        f"house_total_unchanged={shortfall_after2 == shortfall_after} card_cents={after_recon2_cents}",
    )


def main():
    parser = argparse.ArgumentParser(description="Reader simulator for the DEVICE money tier")
    parser.add_argument(
        "--base-url",
        default=None,
        help="If set, run against a live server at this URL (else in-process TestClient).",
    )
    args = parser.parse_args()

    if args.base_url:
        print(f"== Reader simulator :: LIVE mode against {args.base_url} ==")
        client = LiveClient(args.base_url)
    else:
        print("== Reader simulator :: in-process (TestClient) mode ==")
        client = InProcessClient()

    try:
        run(client)
    finally:
        client.close()

    passed = sum(1 for _, ok in _results if ok)
    failed = len(_results) - passed
    print("\n================ READER SIM SUMMARY ================")
    for name, ok in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"\nTOTAL: {passed} PASS / {failed} FAIL  of {len(_results)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
