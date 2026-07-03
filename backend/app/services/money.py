"""Money-path service for the DEVICE / READER tier.

Encapsulates the ledger-consistent charge logic used by both the online
``/charge`` endpoint and the offline ``/reconcile`` replay path. Debits go
through :class:`~app.services.ledger.BalanceLedgerService` so the balance ledger
stays authoritative, and every charge is idempotent on
``(company_id, client_txn_id)``.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.card import Card, CardStatus
from app.models.device import ChargeIdempotency, HouseAccount
from app.services.ledger import BalanceLedgerService

# Sentinel "no tenant" bucket for staff/cashier idempotency records whose
# acting user / card has no company_id (super-admin context). This is purely
# a partition key for the ChargeIdempotency unique index — it has no bearing
# on authorization or tenant isolation, which are enforced independently by
# the calling endpoints before MoneyService is ever invoked.
UNSCOPED_TENANT_ID = uuid.UUID(int=0)


def _cents_to_decimal(cents: int) -> Decimal:
    """Convert integer cents to a 2-dp Decimal (dollars)."""
    return (Decimal(int(cents)) / Decimal(100)).quantize(Decimal("0.01"))


def _decimal_to_cents(amount: Decimal) -> int:
    """Convert a Decimal balance to integer cents."""
    return int((Decimal(amount) * Decimal(100)).to_integral_value())


class MoneyService:
    """Ledger-consistent, idempotent money operations for devices."""

    # ------------------------------------------------------------------ #
    # House accounts
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_or_create_house_account(
        db: Session,
        company_id: uuid.UUID,
        account_type: str = "offline_shortfall",
    ) -> HouseAccount:
        """Fetch (row-locked) or create the company's house account."""
        account = (
            db.query(HouseAccount)
            .filter(
                HouseAccount.company_id == company_id,
                HouseAccount.account_type == account_type,
            )
            .with_for_update()
            .first()
        )
        if account:
            return account

        account = HouseAccount(
            company_id=company_id,
            account_type=account_type,
            balance_cents=0,
        )
        db.add(account)
        try:
            db.flush()
        except IntegrityError:
            # Concurrent create — reload the existing row.
            db.rollback()
            account = (
                db.query(HouseAccount)
                .filter(
                    HouseAccount.company_id == company_id,
                    HouseAccount.account_type == account_type,
                )
                .with_for_update()
                .first()
            )
        return account

    # ------------------------------------------------------------------ #
    # Charge
    # ------------------------------------------------------------------ #
    @staticmethod
    def _existing_idempotency(
        db: Session, company_id: uuid.UUID, client_txn_id: str
    ) -> Optional[ChargeIdempotency]:
        return (
            db.query(ChargeIdempotency)
            .filter(
                ChargeIdempotency.company_id == company_id,
                ChargeIdempotency.client_txn_id == client_txn_id,
            )
            .first()
        )

    @staticmethod
    def _response_from_record(record: ChargeIdempotency) -> Dict[str, Any]:
        return {
            "result": record.result,
            "balance_after_cents": int(record.balance_after_cents)
            if record.balance_after_cents is not None
            else None,
            "server_txn_id": record.server_txn_id,
            "idempotent_replay": True,
        }

    @staticmethod
    def charge(
        db: Session,
        company_id: uuid.UUID,
        card_uid: str,
        price_cents: int,
        client_txn_id: str,
        sku: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None,
        nonce: Optional[str] = None,
        ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Charge a card for ``price_cents`` within ``company_id``.

        Idempotent on ``(company_id, client_txn_id)``: a repeat returns the same
        result without a second debit. Declines (rather than raising) on an
        inactive/absent card or insufficient balance. Debits flow through
        :class:`BalanceLedgerService` so the ledger stays consistent.

        Returns a dict: ``{result, balance_after_cents, server_txn_id,
        idempotent_replay}``.
        """
        if price_cents is None or int(price_cents) <= 0:
            raise ValueError("price_cents must be a positive integer")
        price_cents = int(price_cents)

        # 1) Idempotency short-circuit — never double-process.
        existing = MoneyService._existing_idempotency(db, company_id, client_txn_id)
        if existing:
            return MoneyService._response_from_record(existing)

        # 2) Resolve the card WITHIN the device's company (tenant isolation).
        card = (
            db.query(Card)
            .filter(Card.card_uid == card_uid, Card.company_id == company_id)
            .with_for_update()
            .first()
        )

        def _record_and_return(
            result: str, balance_after_cents: Optional[int]
        ) -> Dict[str, Any]:
            server_txn_id = str(uuid.uuid4())
            record = ChargeIdempotency(
                company_id=company_id,
                client_txn_id=client_txn_id,
                card_uid=card_uid,
                device_id=device_id,
                result=result,
                server_txn_id=server_txn_id,
                balance_after_cents=balance_after_cents,
                price_cents=price_cents,
            )
            db.add(record)
            try:
                db.commit()
            except IntegrityError:
                # A concurrent request won the race on the unique key — return
                # that authoritative result instead of double-processing.
                db.rollback()
                winner = MoneyService._existing_idempotency(
                    db, company_id, client_txn_id
                )
                if winner:
                    return MoneyService._response_from_record(winner)
                raise
            return {
                "result": result,
                "balance_after_cents": balance_after_cents,
                "server_txn_id": server_txn_id,
                "idempotent_replay": False,
            }

        # 3) Decline paths (recorded so replays are stable, no 500s).
        if card is None:
            return _record_and_return("declined", None)

        if card.status != CardStatus.ACTIVE:
            return _record_and_return("declined", _decimal_to_cents(card.balance))

        amount = _cents_to_decimal(price_cents)
        if card.balance < amount:
            return _record_and_return("declined", _decimal_to_cents(card.balance))

        # 4) Approve — debit through the ledger service (row-lock + ledger entry).
        result = BalanceLedgerService.deduct_balance(
            db=db,
            card_uid=card_uid,
            amount=amount,
            user_id=None,
            notes=f"Device charge {sku or ''} (client_txn={client_txn_id})".strip(),
            metadata={
                "source": "device_charge",
                "device_id": str(device_id) if device_id else None,
                "client_txn_id": client_txn_id,
                "sku": sku,
                "nonce": nonce,
                "ts": ts,
                "price_cents": price_cents,
            },
        )
        balance_after_cents = _decimal_to_cents(result["balance_after"])
        return _record_and_return("approved", balance_after_cents)

    # ------------------------------------------------------------------ #
    # Staff / cashier idempotency (generalized reuse of ChargeIdempotency)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _staff_scope_key(endpoint: str, idempotency_key: str) -> str:
        """
        Namespace a staff-supplied idempotency key so it can never collide
        with a device ``client_txn_id`` sharing the same ``charge_idempotency``
        table (and so ``add-credit`` and ``charge`` keys can't collide with
        each other either).
        """
        return f"staff:{endpoint}:{idempotency_key}"

    @staticmethod
    def find_staff_idempotent_response(
        db: Session,
        tenant_id: Optional[uuid.UUID],
        endpoint: str,
        idempotency_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a previously-recorded response for a staff/cashier money
        endpoint call. Returns the stored JSON response dict (with
        ``idempotent_replay: True`` merged in) if this ``(tenant, endpoint,
        idempotency_key)`` was already processed, else ``None``.
        """
        scoped_company_id = tenant_id if tenant_id is not None else UNSCOPED_TENANT_ID
        scope_key = MoneyService._staff_scope_key(endpoint, idempotency_key)

        existing = MoneyService._existing_idempotency(db, scoped_company_id, scope_key)
        if not existing or existing.result_payload is None:
            return None

        response = dict(existing.result_payload)
        response["idempotent_replay"] = True
        return response

    @staticmethod
    def record_staff_idempotent_response(
        db: Session,
        tenant_id: Optional[uuid.UUID],
        endpoint: str,
        idempotency_key: str,
        card_uid: str,
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Persist ``response`` as the canonical result for this ``(tenant,
        endpoint, idempotency_key)`` so a replay returns it without
        re-applying the balance change. Commits immediately (the caller's
        balance mutation is already committed by this point via
        ``BalanceLedgerService``).

        On a unique-constraint race (two concurrent identical requests), the
        winner's stored response is returned instead of raising — mirroring
        the device charge path's concurrency handling.
        """
        scoped_company_id = tenant_id if tenant_id is not None else UNSCOPED_TENANT_ID
        scope_key = MoneyService._staff_scope_key(endpoint, idempotency_key)

        record = ChargeIdempotency(
            company_id=scoped_company_id,
            client_txn_id=scope_key,
            card_uid=card_uid,
            device_id=None,
            result="approved",
            server_txn_id=str(uuid.uuid4()),
            balance_after_cents=None,
            price_cents=None,
            result_payload=response,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            # Concurrent duplicate request already recorded the result first —
            # return that authoritative response rather than erroring.
            db.rollback()
            winner = MoneyService._existing_idempotency(db, scoped_company_id, scope_key)
            if winner and winner.result_payload is not None:
                winner_response = dict(winner.result_payload)
                winner_response["idempotent_replay"] = True
                return winner_response
            raise
        return response

    # ------------------------------------------------------------------ #
    # Reconcile (offline batch replay)
    # ------------------------------------------------------------------ #
    @staticmethod
    def reconcile_batch(
        db: Session,
        company_id: uuid.UUID,
        batch: list,
        key_id: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Replay a batch of offline records idempotently through the charge logic.

        For each record: if the card can cover the price, it is charged normally.
        If the card has insufficient balance (offline overspend), the card is
        driven to 0 and the uncollected remainder is accrued to the company's
        ``offline_shortfall`` house account. Fully-covered and shortfall charges
        both count as applied.

        Returns ``{applied:[server_txn_id...], declined:[...], shortfall_cents}``.
        """
        applied: list = []
        declined: list = []
        total_shortfall_cents = 0

        for item in batch:
            client_txn_id = item.get("client_txn_id")
            card_uid = item.get("card_uid")
            price_cents = int(item.get("price_cents", 0))
            seq = item.get("seq")
            ts = item.get("ts")

            if not client_txn_id or not card_uid or price_cents <= 0:
                declined.append(
                    {
                        "client_txn_id": client_txn_id,
                        "reason": "invalid_record",
                        "seq": seq,
                    }
                )
                continue

            # Idempotency short-circuit for already-applied records.
            existing = MoneyService._existing_idempotency(
                db, company_id, client_txn_id
            )
            if existing:
                if existing.result == "approved":
                    applied.append(existing.server_txn_id)
                else:
                    declined.append(
                        {
                            "client_txn_id": client_txn_id,
                            "reason": "previously_declined",
                            "server_txn_id": existing.server_txn_id,
                            "seq": seq,
                        }
                    )
                continue

            # Resolve card within the company.
            card = (
                db.query(Card)
                .filter(Card.card_uid == card_uid, Card.company_id == company_id)
                .with_for_update()
                .first()
            )

            if card is None or card.status != CardStatus.ACTIVE:
                # Cannot resolve/charge — record a decline (idempotent).
                res = MoneyService._record_offline_result(
                    db,
                    company_id,
                    client_txn_id,
                    card_uid,
                    device_id,
                    "declined",
                    _decimal_to_cents(card.balance) if card else None,
                    price_cents,
                )
                declined.append(
                    {
                        "client_txn_id": client_txn_id,
                        "reason": "card_unavailable",
                        "server_txn_id": res["server_txn_id"],
                        "seq": seq,
                    }
                )
                continue

            current_cents = _decimal_to_cents(card.balance)

            if current_cents >= price_cents:
                # Card covers it — normal ledger debit.
                amount = _cents_to_decimal(price_cents)
                ledger = BalanceLedgerService.deduct_balance(
                    db=db,
                    card_uid=card_uid,
                    amount=amount,
                    user_id=None,
                    notes=f"Offline reconcile (client_txn={client_txn_id})",
                    metadata={
                        "source": "offline_reconcile",
                        "device_id": str(device_id) if device_id else None,
                        "client_txn_id": client_txn_id,
                        "key_id": key_id,
                        "seq": seq,
                        "ts": ts,
                        "price_cents": price_cents,
                    },
                )
                balance_after_cents = _decimal_to_cents(ledger["balance_after"])
                res = MoneyService._record_offline_result(
                    db,
                    company_id,
                    client_txn_id,
                    card_uid,
                    device_id,
                    "approved",
                    balance_after_cents,
                    price_cents,
                )
                applied.append(res["server_txn_id"])
            else:
                # Offline overspend: drain the card to 0, record shortfall.
                shortfall_cents = price_cents - current_cents
                total_shortfall_cents += shortfall_cents

                if current_cents > 0:
                    drain_amount = _cents_to_decimal(current_cents)
                    BalanceLedgerService.deduct_balance(
                        db=db,
                        card_uid=card_uid,
                        amount=drain_amount,
                        user_id=None,
                        notes=(
                            f"Offline reconcile partial (client_txn={client_txn_id}); "
                            f"shortfall {shortfall_cents}c to house account"
                        ),
                        metadata={
                            "source": "offline_reconcile_shortfall",
                            "device_id": str(device_id) if device_id else None,
                            "client_txn_id": client_txn_id,
                            "key_id": key_id,
                            "seq": seq,
                            "ts": ts,
                            "price_cents": price_cents,
                            "collected_cents": current_cents,
                            "shortfall_cents": shortfall_cents,
                        },
                    )

                # Accrue the uncollected remainder to the house account.
                account = MoneyService.get_or_create_house_account(
                    db, company_id, "offline_shortfall"
                )
                account.balance_cents = int(account.balance_cents or 0) + shortfall_cents
                account.updated_at = datetime.utcnow()

                res = MoneyService._record_offline_result(
                    db,
                    company_id,
                    client_txn_id,
                    card_uid,
                    device_id,
                    "approved",  # play was authorized offline; we settle what we can
                    0,  # card floored at 0
                    price_cents,
                )
                applied.append(res["server_txn_id"])

        return {
            "applied": applied,
            "declined": declined,
            "shortfall_cents": total_shortfall_cents,
        }

    @staticmethod
    def _record_offline_result(
        db: Session,
        company_id: uuid.UUID,
        client_txn_id: str,
        card_uid: str,
        device_id: Optional[uuid.UUID],
        result: str,
        balance_after_cents: Optional[int],
        price_cents: int,
    ) -> Dict[str, Any]:
        """Persist an idempotency record for a reconcile item and commit."""
        server_txn_id = str(uuid.uuid4())
        record = ChargeIdempotency(
            company_id=company_id,
            client_txn_id=client_txn_id,
            card_uid=card_uid,
            device_id=device_id,
            result=result,
            server_txn_id=server_txn_id,
            balance_after_cents=balance_after_cents,
            price_cents=price_cents,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            winner = MoneyService._existing_idempotency(db, company_id, client_txn_id)
            if winner:
                return {"server_txn_id": winner.server_txn_id, "result": winner.result}
            raise
        return {"server_txn_id": server_txn_id, "result": result}
