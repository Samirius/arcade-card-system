"""Payments seam (DORMANT STUB).

Defines the *interface* for a future top-up / payment-service-provider (PSP)
integration without wiring a real gateway. This establishes the seam so the
money tier can later accept card/wallet top-ups.

Nothing here talks to a real PSP. The ``/payments/topup-session`` endpoint
returns ``501 Not Implemented`` on purpose.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.device import Device
from app.api.devices import get_current_device

router = APIRouter(prefix="/payments", tags=["payments"])


# --------------------------------------------------------------------------- #
# Typed interface (the seam)
# --------------------------------------------------------------------------- #
class TopUpSession(BaseModel):
    """A hosted top-up/checkout session returned by a PSP."""
    session_id: str
    checkout_url: str
    amount_cents: int
    currency: str = "USD"
    status: str = "created"


@runtime_checkable
class PaymentGateway(Protocol):
    """
    Protocol every concrete PSP adapter (Stripe, Adyen, ...) must satisfy.

    Implementations live behind this seam so the money tier depends on the
    interface, not a specific provider.
    """

    def create_topup_session(
        self,
        *,
        company_id: str,
        card_uid: str,
        amount_cents: int,
        currency: str = "USD",
        idempotency_key: Optional[str] = None,
    ) -> TopUpSession:
        """Create a hosted top-up session for the given card."""
        ...

    def verify_webhook(self, *, payload: bytes, signature: str) -> bool:
        """Verify an inbound PSP webhook signature."""
        ...


class NullPaymentGateway:
    """
    Default no-op gateway. Present so dependency wiring exists; every method
    raises ``NotImplementedError`` because no PSP is integrated yet.
    """

    def create_topup_session(self, **_kwargs) -> TopUpSession:  # pragma: no cover - stub
        raise NotImplementedError("No payment gateway configured (dormant stub)")

    def verify_webhook(self, **_kwargs) -> bool:  # pragma: no cover - stub
        raise NotImplementedError("No payment gateway configured (dormant stub)")


def get_payment_gateway() -> PaymentGateway:
    """Dependency provider for the active PSP adapter (currently the null one)."""
    return NullPaymentGateway()


# --------------------------------------------------------------------------- #
# Dormant endpoint
# --------------------------------------------------------------------------- #
class TopUpSessionRequest(BaseModel):
    card_uid: str = Field(..., min_length=1, max_length=255)
    amount_cents: int = Field(..., gt=0)
    currency: str = Field("USD", max_length=8)


@router.post("/topup-session", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_topup_session(
    body: TopUpSessionRequest,
    device: Device = Depends(get_current_device),
    gateway: PaymentGateway = Depends(get_payment_gateway),
    db=Depends(get_db),
):
    """
    Create a top-up session (DORMANT).

    The seam is defined but no PSP is integrated, so this always returns
    ``501 Not Implemented``.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Payment top-up is not implemented yet (dormant PSP seam).",
    )
