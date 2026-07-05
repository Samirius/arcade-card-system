"""
BE-6: Money-path depth tests (staff / cashier tier).

Covers, with real assertions against the live FastAPI app + PostgreSQL:
    * staff add-credit + charge (happy path, balance moves correctly)
    * insufficient-balance charge is declined with 400 (never 500)
    * idempotency on the staff path: the SAME Idempotency-Key (or
      client_txn_id) applied twice only moves the balance ONCE, and the
      replay response is marked idempotent_replay=True

Balance "ground truth" is read directly from the database (not via
``GET /cards/{uid}``): that endpoint runs ``_check_card_tenant_access``,
which -- for a company_id-less card -- only allows the creator through
when ``card.owner`` matches the creator's email/full name. These tests use
an arbitrary ``owner`` value (as the real verification harness does), so a
direct DB read is both simpler and a stronger ground-truth check anyway.
"""
from decimal import Decimal

from app.models.card import Card

from tests.conftest import (
    API,
    auth_headers,
    register_verify_login,
    create_card,
)


def _get_balance(db_session, card_uid: str) -> Decimal:
    db_session.expire_all()
    card = db_session.query(Card).filter(Card.card_uid == card_uid).first()
    assert card is not None, f"card {card_uid} not found in DB"
    return Decimal(str(card.balance))


class TestStaffAddCreditAndCharge:
    def test_add_credit_increases_balance(self, client, db_session):
        _, token, _ = register_verify_login(client, role="STAFF")
        rc = create_card(client, token, initial_balance=0)
        assert rc.status_code == 201, rc.text
        card_uid = rc.json()["card_uid"]

        r = client.post(
            f"{API}/cards/{card_uid}/add-credit",
            headers=auth_headers(token),
            json={"amount": "25.00", "notes": "cash top-up"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert Decimal(str(body["old_balance"])) == Decimal("0.00")
        assert Decimal(str(body["new_balance"])) == Decimal("25.00")
        assert body["idempotent_replay"] is False

        assert _get_balance(db_session, card_uid) == Decimal("25.00")

    def test_charge_decreases_balance(self, client, db_session):
        _, token, _ = register_verify_login(client, role="STAFF")
        rc = create_card(client, token, initial_balance=Decimal("50.00"))
        assert rc.status_code == 201, rc.text
        card_uid = rc.json()["card_uid"]

        r = client.post(
            f"{API}/cards/{card_uid}/charge",
            headers=auth_headers(token),
            json={"amount": "12.50", "notes": "arcade play"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert Decimal(str(body["old_balance"])) == Decimal("50.00")
        assert Decimal(str(body["new_balance"])) == Decimal("37.50")
        assert Decimal(str(body["amount_charged"])) == Decimal("12.50")

        assert _get_balance(db_session, card_uid) == Decimal("37.50")

    def test_charge_insufficient_balance_declines_400_not_500(self, client, db_session):
        _, token, _ = register_verify_login(client, role="STAFF")
        rc = create_card(client, token, initial_balance=Decimal("5.00"))
        assert rc.status_code == 201, rc.text
        card_uid = rc.json()["card_uid"]

        r = client.post(
            f"{API}/cards/{card_uid}/charge",
            headers=auth_headers(token),
            json={"amount": "999.00"},
        )
        assert r.status_code == 400, r.text
        assert "insufficient" in r.text.lower()

        # Balance must be UNCHANGED after a declined charge.
        assert _get_balance(db_session, card_uid) == Decimal("5.00")

    def test_charge_nonexistent_card_returns_404_not_500(self, client):
        _, token, _ = register_verify_login(client, role="STAFF")
        r = client.post(
            f"{API}/cards/DOES-NOT-EXIST-CARD/charge",
            headers=auth_headers(token),
            json={"amount": "1.00"},
        )
        assert r.status_code == 404


class TestStaffIdempotency:
    def test_add_credit_idempotency_key_header_applied_once(self, client, db_session):
        _, token, _ = register_verify_login(client, role="STAFF")
        rc = create_card(client, token, initial_balance=0)
        card_uid = rc.json()["card_uid"]

        idem_key = "add-credit-test-key-001"

        r1 = client.post(
            f"{API}/cards/{card_uid}/add-credit",
            headers={**auth_headers(token), "Idempotency-Key": idem_key},
            json={"amount": "10.00"},
        )
        assert r1.status_code == 200, r1.text
        body1 = r1.json()
        assert body1["idempotent_replay"] is False
        assert Decimal(str(body1["new_balance"])) == Decimal("10.00")

        # Replay the EXACT same key.
        r2 = client.post(
            f"{API}/cards/{card_uid}/add-credit",
            headers={**auth_headers(token), "Idempotency-Key": idem_key},
            json={"amount": "10.00"},
        )
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["idempotent_replay"] is True
        # Same stored result -- balance must NOT have moved a second time.
        assert Decimal(str(body2["new_balance"])) == Decimal("10.00")

        # Ground truth: only ONE 10.00 credit was ever applied.
        assert _get_balance(db_session, card_uid) == Decimal("10.00")

    def test_charge_idempotency_client_txn_id_body_applied_once(self, client, db_session):
        _, token, _ = register_verify_login(client, role="STAFF")
        rc = create_card(client, token, initial_balance=Decimal("100.00"))
        card_uid = rc.json()["card_uid"]

        payload = {"amount": "15.00", "client_txn_id": "charge-idem-txn-abc"}

        r1 = client.post(
            f"{API}/cards/{card_uid}/charge", headers=auth_headers(token), json=payload
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["idempotent_replay"] is False
        assert Decimal(str(r1.json()["new_balance"])) == Decimal("85.00")

        r2 = client.post(
            f"{API}/cards/{card_uid}/charge", headers=auth_headers(token), json=payload
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["idempotent_replay"] is True
        assert Decimal(str(r2.json()["new_balance"])) == Decimal("85.00")

        # Ground truth: the card was only charged ONCE (85, not 70).
        assert _get_balance(db_session, card_uid) == Decimal("85.00")

    def test_different_idempotency_keys_both_apply(self, client, db_session):
        """Sanity check the idempotency scoping isn't accidentally global:
        two DIFFERENT keys against the same card must both take effect."""
        _, token, _ = register_verify_login(client, role="STAFF")
        rc = create_card(client, token, initial_balance=0)
        card_uid = rc.json()["card_uid"]

        r1 = client.post(
            f"{API}/cards/{card_uid}/add-credit",
            headers={**auth_headers(token), "Idempotency-Key": "key-A"},
            json={"amount": "5.00"},
        )
        r2 = client.post(
            f"{API}/cards/{card_uid}/add-credit",
            headers={**auth_headers(token), "Idempotency-Key": "key-B"},
            json={"amount": "5.00"},
        )
        assert r1.status_code == 200 and r2.status_code == 200
        assert _get_balance(db_session, card_uid) == Decimal("10.00")
