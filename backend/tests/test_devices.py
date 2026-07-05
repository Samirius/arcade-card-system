"""
BE-6: Device / reader money-path depth tests.

Covers, with real assertions against the live FastAPI app + PostgreSQL:
    * device enrollment (OWNER bound to a real company)
    * idempotency on device POST /api/v1/charge: the same client_txn_id
      applied twice returns the same server_txn_id and does NOT double-debit
    * POST /api/v1/reconcile offline overspend: shortfall accrues to the
      company's offline_shortfall HouseAccount and the card is floored at 0
"""
import uuid
from decimal import Decimal

from app.models.card import Card, CardType, CardStatus
from app.models.device import HouseAccount

from tests.conftest import (
    API,
    auth_headers,
    login_user,
    seed_company_and_owner,
    enroll_device,
)


def _login_owner(client, db_session):
    """Seed a Company + ACTIVE OWNER, then log in via the real HTTP flow."""
    email, password, company_id = seed_company_and_owner(db_session)
    r = login_user(client, email, password=password)
    assert r.status_code == 200, f"owner login failed: {r.status_code} {r.text}"
    return email, r.json()["access_token"], company_id


def _make_card(db_session, company_id, balance: Decimal, card_uid: str = None) -> str:
    """Directly insert an ACTIVE card scoped to company_id with a given balance."""
    if card_uid is None:
        card_uid = f"DEV{uuid.uuid4().hex[:10].upper()}"
    card = Card(
        card_uid=card_uid,
        owner="Device Test Card",
        card_type=CardType.REGULAR,
        status=CardStatus.ACTIVE,
        balance=balance,
        company_id=company_id,
    )
    db_session.add(card)
    db_session.commit()
    return card_uid


def _get_balance(db_session, card_uid: str) -> Decimal:
    db_session.expire_all()
    card = db_session.query(Card).filter(Card.card_uid == card_uid).first()
    assert card is not None
    return Decimal(str(card.balance))


def _get_shortfall_cents(db_session, company_id) -> int:
    db_session.expire_all()
    account = (
        db_session.query(HouseAccount)
        .filter(
            HouseAccount.company_id == company_id,
            HouseAccount.account_type == "offline_shortfall",
        )
        .first()
    )
    return int(account.balance_cents) if account else 0


class TestDeviceEnrollment:
    def test_owner_can_enroll_device(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)

        r = enroll_device(client, owner_token, label="Front Desk Reader")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["label"] == "Front Desk Reader"
        assert body["status"] == "ACTIVE"
        assert str(body["company_id"]) == str(company_id)
        assert body["device_token"].startswith("dev_")

    def test_staff_cannot_enroll_device(self, client, db_session):
        from tests.conftest import register_verify_login

        _, staff_token, _ = register_verify_login(client, role="STAFF")
        r = enroll_device(client, staff_token, label="Should Fail")
        assert r.status_code == 403


class TestDeviceChargeIdempotency:
    def test_charge_debits_card_once(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)
        card_uid = _make_card(db_session, company_id, Decimal("50.00"))

        r_enroll = enroll_device(client, owner_token)
        assert r_enroll.status_code == 201, r_enroll.text
        device_token = r_enroll.json()["device_token"]

        r = client.post(
            f"{API}/charge",
            headers=auth_headers(device_token),
            json={
                "card_uid": card_uid,
                "price_cents": 1500,
                "client_txn_id": str(uuid.uuid4()),
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["result"] == "approved"
        assert body["balance_after_cents"] == 3500
        assert body["idempotent_replay"] is False

        assert _get_balance(db_session, card_uid) == Decimal("35.00")

    def test_repeated_client_txn_id_does_not_double_debit(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)
        card_uid = _make_card(db_session, company_id, Decimal("50.00"))

        device_token = enroll_device(client, owner_token).json()["device_token"]
        client_txn_id = str(uuid.uuid4())

        r1 = client.post(
            f"{API}/charge",
            headers=auth_headers(device_token),
            json={"card_uid": card_uid, "price_cents": 2000, "client_txn_id": client_txn_id},
        )
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        assert body1["result"] == "approved"
        assert body1["idempotent_replay"] is False
        server_txn_id_1 = body1["server_txn_id"]

        # Exact same client_txn_id -- must be a no-op replay.
        r2 = client.post(
            f"{API}/charge",
            headers=auth_headers(device_token),
            json={"card_uid": card_uid, "price_cents": 2000, "client_txn_id": client_txn_id},
        )
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["idempotent_replay"] is True
        assert body2["server_txn_id"] == server_txn_id_1
        assert body2["balance_after_cents"] == body1["balance_after_cents"]

        # Ground truth: only ONE $20.00 debit was ever applied (50 - 20 = 30).
        assert _get_balance(db_session, card_uid) == Decimal("30.00")

    def test_charge_insufficient_balance_declines_not_500(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)
        card_uid = _make_card(db_session, company_id, Decimal("2.00"))
        device_token = enroll_device(client, owner_token).json()["device_token"]

        r = client.post(
            f"{API}/charge",
            headers=auth_headers(device_token),
            json={"card_uid": card_uid, "price_cents": 99999, "client_txn_id": str(uuid.uuid4())},
        )
        assert r.status_code == 200, r.text
        assert r.json()["result"] == "declined"
        # Declined charges never touch the balance.
        assert _get_balance(db_session, card_uid) == Decimal("2.00")

    def test_charge_without_device_token_rejected(self, client):
        r = client.post(
            f"{API}/charge",
            json={"card_uid": "whatever", "price_cents": 100, "client_txn_id": str(uuid.uuid4())},
        )
        assert r.status_code == 401


class TestReconcileOverspend:
    def test_overspend_floors_card_and_accrues_shortfall(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)
        # Card only has $3.00 but the offline device authorized a $10.00 charge.
        card_uid = _make_card(db_session, company_id, Decimal("3.00"))
        device_token = enroll_device(client, owner_token).json()["device_token"]

        r = client.post(
            f"{API}/reconcile",
            headers=auth_headers(device_token),
            json={
                "batch": [
                    {
                        "card_uid": card_uid,
                        "price_cents": 1000,
                        "client_txn_id": str(uuid.uuid4()),
                        "seq": 1,
                    }
                ],
                "key_id": "reconcile-test-batch-1",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["applied"]) == 1
        assert len(body["declined"]) == 0
        # Shortfall = 1000 - 300 = 700 cents.
        assert body["shortfall_cents"] == 700

        # Card must be floored at exactly 0, never negative.
        assert _get_balance(db_session, card_uid) == Decimal("0.00")

        # The shortfall must be accrued to the company's offline_shortfall house account.
        assert _get_shortfall_cents(db_session, company_id) == 700

    def test_fully_covered_reconcile_item_has_no_shortfall(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)
        card_uid = _make_card(db_session, company_id, Decimal("20.00"))
        device_token = enroll_device(client, owner_token).json()["device_token"]

        r = client.post(
            f"{API}/reconcile",
            headers=auth_headers(device_token),
            json={
                "batch": [
                    {
                        "card_uid": card_uid,
                        "price_cents": 500,
                        "client_txn_id": str(uuid.uuid4()),
                        "seq": 1,
                    }
                ]
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["applied"]) == 1
        assert body["shortfall_cents"] == 0
        assert _get_balance(db_session, card_uid) == Decimal("15.00")

    def test_reconcile_batch_is_idempotent_per_item(self, client, db_session):
        _, owner_token, company_id = _login_owner(client, db_session)
        card_uid = _make_card(db_session, company_id, Decimal("3.00"))
        device_token = enroll_device(client, owner_token).json()["device_token"]

        shared_txn_id = str(uuid.uuid4())
        batch_payload = {
            "batch": [
                {"card_uid": card_uid, "price_cents": 1000, "client_txn_id": shared_txn_id, "seq": 1}
            ],
            "key_id": "reconcile-idem-test",
        }

        r1 = client.post(f"{API}/reconcile", headers=auth_headers(device_token), json=batch_payload)
        assert r1.status_code == 200, r1.text
        assert r1.json()["shortfall_cents"] == 700

        # Replaying the identical batch must NOT accrue shortfall again.
        r2 = client.post(f"{API}/reconcile", headers=auth_headers(device_token), json=batch_payload)
        assert r2.status_code == 200, r2.text
        assert r2.json()["shortfall_cents"] == 0  # nothing NEW applied this call
        assert len(r2.json()["applied"]) == 1  # but it's still reported as applied (replay)

        # Ground truth: shortfall accrued exactly once (700, not 1400).
        assert _get_shortfall_cents(db_session, company_id) == 700
        assert _get_balance(db_session, card_uid) == Decimal("0.00")
