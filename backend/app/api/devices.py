"""Device / reader API — enrollment, management, and the money path.

This module implements the DEVICE / READER money tier:

* Device enrollment & lifecycle (admin/owner authenticated).
* ``get_current_device`` — bearer-token auth for readers.
* The money path: ``POST /charge`` and ``POST /reconcile`` (device authenticated).
* Offline authorization envelopes signed with Ed25519, plus the public key.

Two routers are exported and both are mounted under the app's ``/api/v1`` prefix:
* ``router``        → ``/api/v1/devices/*``
* ``money_router``  → ``/api/v1/charge`` and ``/api/v1/reconcile``

Security note:
    Devices authenticate with an opaque bearer ``device_token`` (only its
    SHA-256 hash is stored). mTLS / X.509 client certificates are the intended
    PRODUCTION upgrade for device identity; the bearer token is the pragmatic
    pilot credential.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.device import Device, DeviceStatus
from app.schemas.device import (
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DeviceResponse,
    ChargeRequest,
    ChargeResponse,
    ReconcileRequest,
    ReconcileResponse,
    OfflineEnvelopeResponse,
    OfflinePubkeyResponse,
)
from app.api.auth import get_current_user, set_tenant_context, begin_credential_lookup
from app.api.authorization import require_role
from app.services.money import MoneyService
from app.utils import signing
from app.utils.audit import log_action

router = APIRouter(prefix="/devices", tags=["devices"])
money_router = APIRouter(tags=["money"])

# Bearer scheme for device tokens (distinct usage from user JWTs).
device_security = HTTPBearer(auto_error=False)

# Offline authorization envelope defaults (cents). Tunable per deployment.
DEFAULT_OFFLINE_CAP_CENTS = 5000        # total the reader may authorize offline
DEFAULT_PER_TXN_CAP_CENTS = 1000        # per-transaction ceiling offline
DEFAULT_ENVELOPE_TTL_MINUTES = 60       # envelope validity window


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a device token."""
    return sha256(token.encode("utf-8")).hexdigest()


async def get_current_device(
    credentials: HTTPAuthorizationCredentials = Depends(device_security),
    db: Session = Depends(get_db),
) -> Device:
    """
    Authenticate a device by ``Authorization: Bearer <device_token>``.

    Hash-compares the presented token against ``device_token_hash``. Yields the
    :class:`Device` (whose ``company_id`` scopes all money operations). Raises
    401 if missing/invalid, 403 if the device is not ACTIVE.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # A device is authenticated by its global token hash, which exists BEFORE
    # any tenant context. `devices` is under RLS, so open a narrow bypass window
    # for just this credential lookup; the real (device-scoped) tenant context
    # is pinned immediately after via set_tenant_context below.
    begin_credential_lookup(db)

    token_hash = _hash_token(credentials.credentials)
    device = db.query(Device).filter(Device.device_token_hash == token_hash).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if device.status != DeviceStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is not active",
        )

    # Capture the device's tenant key WHILE it is still loaded under the
    # credential-lookup bypass window opened above, and BEFORE the liveness
    # commit below expires it. If we read this attribute after the commit it
    # would trigger a lazy reload in a transaction that has no tenant context
    # yet (the bypass is transaction-scoped and cleared by the commit), and RLS
    # would then hide the device's own row.
    device_company_id = device.company_id

    # Best-effort liveness tracking (does not block the request on failure).
    try:
        device.last_seen_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()

    # Bind the per-request RLS tenant context AFTER the liveness commit above:
    # set_config(..., is_local=true) is transaction-scoped, and the commit ends
    # that transaction. set_tenant_context also stashes the context on the
    # session so the after_begin listener re-applies it to every subsequent
    # transaction in this request — so all money queries are scoped to the
    # device's company. Devices are never super-admin.
    set_tenant_context(
        db,
        company_id=device_company_id,
        is_superadmin=False,
    )

    # The liveness commit expired ``device``'s attributes. Eagerly reload it now,
    # WITHIN the tenant-scoped transaction just opened by set_tenant_context, so
    # the /charge & /reconcile endpoints can read ``device.id`` /
    # ``device.company_id`` without a lazy reload landing in an unscoped
    # transaction. The device belongs to ``device_company_id`` — exactly the
    # tenant now in force — so it is visible.
    db.refresh(device)

    return device


# --------------------------------------------------------------------------- #
# Enrollment & management (admin/owner)
# --------------------------------------------------------------------------- #
@router.post("/enroll", response_model=DeviceEnrollResponse, status_code=status.HTTP_201_CREATED)
async def enroll_device(
    body: DeviceEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
):
    """
    Enroll a new device bound to the caller's company.

    **Permissions:** ADMIN / OWNER.

    Returns a one-time plaintext ``device_token`` (only its hash is stored).
    This token is the device's bearer credential for the money path.
    """
    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrolling user is not bound to a company; cannot scope device.",
        )

    # Generate a high-entropy opaque token; persist only its hash.
    plaintext_token = f"dev_{secrets.token_urlsafe(32)}"
    token_hash = _hash_token(plaintext_token)

    device = Device(
        company_id=company_id,
        label=body.label,
        venue=body.venue,
        device_token_hash=token_hash,
        status=DeviceStatus.ACTIVE,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    log_action(
        db=db,
        user_id=current_user.id,
        action="DEVICE_ENROLL",
        details=f"Enrolled device {device.id} ({device.label}) for company {company_id}",
    )

    return DeviceEnrollResponse(
        id=device.id,
        company_id=device.company_id,
        label=device.label,
        venue=device.venue,
        status=device.status.value,
        device_token=plaintext_token,
        created_at=device.created_at,
    )


@router.get("", response_model=List[DeviceResponse])
@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
):
    """
    List devices for the caller's company.

    **Permissions:** ADMIN / OWNER. OWNER with no company sees all devices.
    """
    query = db.query(Device)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        query = query.filter(Device.company_id == company_id)
    devices = query.order_by(Device.created_at.desc()).all()
    return [
        DeviceResponse(
            id=d.id,
            company_id=d.company_id,
            label=d.label,
            venue=d.venue,
            status=d.status.value,
            created_at=d.created_at,
            revoked_at=d.revoked_at,
            last_seen_at=d.last_seen_at,
        )
        for d in devices
    ]


@router.post("/{device_id}/revoke", response_model=DeviceResponse)
async def revoke_device(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OWNER"])),
):
    """
    Revoke a device (its token can no longer authenticate).

    **Permissions:** ADMIN / OWNER, scoped to the caller's company.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    company_id = getattr(current_user, "company_id", None)
    if company_id is not None and device.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device belongs to another company",
        )

    device.status = DeviceStatus.REVOKED
    device.revoked_at = datetime.utcnow()
    db.commit()
    db.refresh(device)

    log_action(
        db=db,
        user_id=current_user.id,
        action="DEVICE_REVOKE",
        details=f"Revoked device {device.id}",
    )

    return DeviceResponse(
        id=device.id,
        company_id=device.company_id,
        label=device.label,
        venue=device.venue,
        status=device.status.value,
        created_at=device.created_at,
        revoked_at=device.revoked_at,
        last_seen_at=device.last_seen_at,
    )


# --------------------------------------------------------------------------- #
# Offline authorization envelope + public key
# --------------------------------------------------------------------------- #
@router.get("/offline-pubkey", response_model=OfflinePubkeyResponse)
async def offline_pubkey():
    """
    Return the server's Ed25519 public key used to sign offline envelopes.

    Public endpoint — readers/auditors fetch this to verify envelope signatures.
    """
    return OfflinePubkeyResponse(
        key_id=signing.KEY_ID,
        algorithm="Ed25519",
        public_key_b64=signing.get_public_key_b64(),
        public_key_pem=signing.get_public_key_pem(),
    )


@router.get("/{device_id}/offline-envelope", response_model=OfflineEnvelopeResponse)
async def offline_envelope(
    device_id: uuid.UUID,
    device: Device = Depends(get_current_device),
):
    """
    Issue a signed offline authorization envelope for the authenticated device.

    **Auth:** device bearer token. The ``device_id`` in the path must match the
    authenticated device. The envelope tells the reader how much it may
    authorize while offline; ``signature`` is Ed25519 over canonical JSON of the
    payload (verifiable with ``/devices/offline-pubkey``).
    """
    if device.id != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Envelope requested for a device other than the authenticated one",
        )

    valid_until = (datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_ENVELOPE_TTL_MINUTES)).isoformat()

    # Canonical payload that gets signed (signature field excluded).
    payload = {
        "device_id": str(device.id),
        "offline_cap_cents": DEFAULT_OFFLINE_CAP_CENTS,
        "per_txn_cap_cents": DEFAULT_PER_TXN_CAP_CENTS,
        "valid_until": valid_until,
        "key_id": signing.KEY_ID,
    }
    signature = signing.sign_payload(payload)

    return OfflineEnvelopeResponse(
        device_id=payload["device_id"],
        offline_cap_cents=payload["offline_cap_cents"],
        per_txn_cap_cents=payload["per_txn_cap_cents"],
        valid_until=payload["valid_until"],
        key_id=payload["key_id"],
        signature=signature,
    )


# --------------------------------------------------------------------------- #
# Money path (device authenticated)
# --------------------------------------------------------------------------- #
@money_router.post("/charge", response_model=ChargeResponse)
async def charge(
    body: ChargeRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    """
    Charge a card via an authenticated reader.

    **Auth:** device bearer token.

    Resolves the card within the device's company, debits via the balance
    ledger (row-locked + ledger entry), and is idempotent on
    ``(company_id, client_txn_id)`` — a repeat returns the same result without a
    second debit. Declines (not 500) on an inactive/unknown card or insufficient
    balance.
    """
    try:
        result = MoneyService.charge(
            db=db,
            company_id=device.company_id,
            card_uid=body.card_uid,
            price_cents=body.price_cents,
            client_txn_id=body.client_txn_id,
            sku=body.sku,
            device_id=device.id,
            nonce=body.nonce,
            ts=body.ts,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ChargeResponse(
        result=result["result"],
        balance_after_cents=result["balance_after_cents"],
        server_txn_id=result["server_txn_id"],
        idempotent_replay=result.get("idempotent_replay", False),
    )


@money_router.post("/reconcile", response_model=ReconcileResponse)
async def reconcile(
    body: ReconcileRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    """
    Replay a batch of offline transactions idempotently.

    **Auth:** device bearer token.

    Each record runs through the same idempotent charge logic. On offline
    overspend the card is floored at 0 and the shortfall is accrued to the
    company's ``offline_shortfall`` house account.
    """
    batch = [item.model_dump() for item in body.batch]
    result = MoneyService.reconcile_batch(
        db=db,
        company_id=device.company_id,
        batch=batch,
        key_id=body.key_id,
        device_id=device.id,
    )
    return ReconcileResponse(
        applied=result["applied"],
        declined=result["declined"],
        shortfall_cents=result["shortfall_cents"],
    )
