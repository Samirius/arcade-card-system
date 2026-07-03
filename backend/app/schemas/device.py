"""Pydantic schemas for the DEVICE / READER money tier."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enrollment / management
# --------------------------------------------------------------------------- #
class DeviceEnrollRequest(BaseModel):
    """Request body for enrolling a new device."""
    label: str = Field(..., min_length=1, max_length=255, description="Human-readable device label")
    venue: Optional[str] = Field(None, max_length=255, description="Venue / location name")


class DeviceEnrollResponse(BaseModel):
    """Enrollment response. ``device_token`` is returned exactly ONCE."""
    id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    label: str
    venue: Optional[str] = None
    status: str
    device_token: str = Field(..., description="One-time plaintext bearer token. Store securely; only the hash is persisted.")
    created_at: Optional[datetime] = None


class DeviceResponse(BaseModel):
    """Device metadata (never exposes the token)."""
    id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    label: str
    venue: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


# --------------------------------------------------------------------------- #
# Money path
# --------------------------------------------------------------------------- #
class ChargeRequest(BaseModel):
    """Body for ``POST /charge`` (device-authenticated)."""
    card_uid: str = Field(..., min_length=1, max_length=255)
    price_cents: int = Field(..., gt=0, description="Amount to charge, in integer cents")
    sku: Optional[str] = Field(None, max_length=255)
    client_txn_id: str = Field(..., min_length=1, max_length=255, description="Client-generated idempotency key (uuid)")
    nonce: Optional[str] = Field(None, max_length=255)
    ts: Optional[str] = Field(None, max_length=64, description="Client timestamp (ISO)")


class ChargeResponse(BaseModel):
    result: str  # approved | declined
    balance_after_cents: Optional[int] = None
    server_txn_id: str
    idempotent_replay: bool = False


class ReconcileItem(BaseModel):
    card_uid: str = Field(..., min_length=1, max_length=255)
    price_cents: int = Field(..., gt=0)
    client_txn_id: str = Field(..., min_length=1, max_length=255)
    seq: Optional[int] = None
    ts: Optional[str] = Field(None, max_length=64)


class ReconcileRequest(BaseModel):
    batch: List[ReconcileItem]
    key_id: Optional[str] = Field(None, max_length=128)


class ReconcileResponse(BaseModel):
    applied: List[str]
    declined: List[dict]
    shortfall_cents: int


# --------------------------------------------------------------------------- #
# Offline authorization envelope
# --------------------------------------------------------------------------- #
class OfflineEnvelopeResponse(BaseModel):
    device_id: str
    offline_cap_cents: int
    per_txn_cap_cents: int
    valid_until: str  # ISO timestamp
    key_id: str
    signature: str  # base64 Ed25519 over canonical JSON of the payload


class OfflinePubkeyResponse(BaseModel):
    key_id: str
    algorithm: str
    public_key_b64: str
    public_key_pem: str
