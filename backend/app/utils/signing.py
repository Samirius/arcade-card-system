"""Ed25519 signing for offline authorization envelopes.

The DEVICE money tier hands each reader a short-lived, signed *offline
authorization envelope* that tells the reader how much it may authorize while
disconnected. Readers (and auditors) verify the envelope's Ed25519 signature
against the server's published public key.

Key management (in priority order):
    1. ``OFFLINE_SIGNING_KEY`` env var — a 32-byte Ed25519 private seed, provided
       as base64 or hex. This is the production-friendly path (inject via secret
       manager).
    2. A persisted key file (``OFFLINE_SIGNING_KEY_PATH`` or a default under the
       backend dir). Generated once on first use and reused thereafter, so the
       public key is stable across restarts in the pilot.

Canonical JSON:
    Payloads are serialized with ``json.dumps(payload, sort_keys=True,
    separators=(",", ":"))`` so signing and verification agree byte-for-byte.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# Key identifier surfaced in envelopes so a reader knows which public key to use.
KEY_ID = "offline-ed25519-v1"

_lock = threading.Lock()
_private_key: Ed25519PrivateKey | None = None


def _default_key_path() -> Path:
    """Default on-disk location for the persisted signing key."""
    override = os.getenv("OFFLINE_SIGNING_KEY_PATH")
    if override:
        return Path(override)
    # backend/ directory (two parents up from this file: utils -> app -> backend)
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir / ".offline_signing_key"


def _decode_seed(raw: str) -> bytes:
    """Decode a 32-byte Ed25519 seed from base64 or hex text."""
    raw = raw.strip()
    # Try hex first (64 hex chars == 32 bytes)
    try:
        if len(raw) == 64:
            return binascii.unhexlify(raw)
    except (binascii.Error, ValueError):
        pass
    # Fall back to base64 (accept url-safe and standard, with/without padding)
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            padded = raw + "=" * (-len(raw) % 4)
            seed = decoder(padded)
            if len(seed) == 32:
                return seed
        except (binascii.Error, ValueError):
            continue
    raise ValueError(
        "OFFLINE_SIGNING_KEY must be a 32-byte Ed25519 seed encoded as hex or base64"
    )


def _load_or_create_key() -> Ed25519PrivateKey:
    """Load the private key from env/file, generating+persisting if needed."""
    # 1) Environment-provided seed (highest priority).
    env_seed = os.getenv("OFFLINE_SIGNING_KEY")
    if env_seed:
        seed = _decode_seed(env_seed)
        return Ed25519PrivateKey.from_private_bytes(seed)

    # 2) Persisted key file.
    key_path = _default_key_path()
    if key_path.exists():
        try:
            raw = key_path.read_bytes()
            return serialization.load_pem_private_key(raw, password=None)
        except Exception:
            # Corrupt/unreadable — fall through to regenerate.
            pass

    # 3) Generate + persist.
    key = Ed25519PrivateKey.generate()
    try:
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(pem)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
    except OSError:
        # If we cannot persist (read-only fs), keep the in-memory key for this
        # process. The public key stays stable for the process lifetime.
        pass
    return key


def get_private_key() -> Ed25519PrivateKey:
    """Return the process-wide Ed25519 private key (lazy, thread-safe)."""
    global _private_key
    if _private_key is None:
        with _lock:
            if _private_key is None:
                _private_key = _load_or_create_key()
    return _private_key


def get_public_key() -> Ed25519PublicKey:
    """Return the Ed25519 public key derived from the signing key."""
    return get_private_key().public_key()


def get_public_key_b64() -> str:
    """Return the raw public key bytes as standard base64 (for distribution)."""
    raw = get_public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def get_public_key_pem() -> str:
    """Return the public key in PEM (SubjectPublicKeyInfo) form."""
    pem = get_public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem.decode("ascii")


def canonical_json(payload: Dict[str, Any]) -> bytes:
    """Serialize a payload to canonical (sorted, compact) JSON bytes."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_payload(payload: Dict[str, Any]) -> str:
    """Sign a canonical-JSON payload, returning a base64 Ed25519 signature."""
    signature = get_private_key().sign(canonical_json(payload))
    return base64.b64encode(signature).decode("ascii")


def verify_payload(payload: Dict[str, Any], signature_b64: str) -> bool:
    """Verify a base64 Ed25519 signature over a canonical-JSON payload."""
    try:
        signature = base64.b64decode(signature_b64)
        get_public_key().verify(signature, canonical_json(payload))
        return True
    except (InvalidSignature, ValueError, binascii.Error):
        return False
