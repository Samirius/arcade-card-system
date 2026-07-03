// =============================================================================
// offline_store.h  --  Signed offline envelope + append-only local txn log
// =============================================================================
// Two responsibilities:
//
// 1) ENVELOPE: cache and verify the server-signed offline authorization envelope
//    ( GET /api/v1/devices/{id}/offline-envelope ):
//        { offline_cap_cents, per_txn_cap_cents, valid_until, key_id, signature }
//    The signature is Ed25519 over a CANONICAL message string (see
//    envelopeCanonicalMessage) and is verified against the pinned public key in
//    config.h. Only a valid, unexpired, correctly-key_id'd envelope permits any
//    offline authorization. Caps are enforced as:
//      - per_txn_cap_cents : max single offline charge
//      - offline_cap_cents : max cumulative offline spend since last reconcile
//
// 2) LOG: an append-only record of offline-authorized charges, persisted in NVS.
//    Each record carries {card_uid, price_cents, client_txn_id, seq, ts} plus an
//    HMAC-SHA256 tag (device-local key) so a record cannot be silently edited on
//    the device. Records are uploaded via POST /api/v1/reconcile and only pruned
//    after the server acknowledges them.
// =============================================================================
#pragma once

#include <Arduino.h>
#include <stdint.h>

// Parsed + verified offline envelope.
struct OfflineEnvelope {
    bool     valid = false;         // signature verified, key_id matched
    uint32_t offlineCapCents = 0;   // cumulative cap since last reconcile
    uint32_t perTxnCapCents = 0;    // per-transaction cap
    uint64_t validUntilEpoch = 0;   // unix seconds; 0 = unknown
    String   keyId;
};

// One offline-authorized charge awaiting reconciliation.
struct OfflineRecord {
    String   cardUid;
    uint32_t priceCents = 0;
    String   clientTxnId;   // UUIDv4, matches the eventual charge idempotency key
    uint32_t seq = 0;
    uint64_t ts = 0;        // unix seconds at authorization time
};

namespace offline {

// Load any previously-cached envelope from NVS and verify it. Safe to call in
// setup(); leaves getEnvelope().valid=false if none/invalid/expired.
void begin();

// Store a freshly-fetched envelope: parse the JSON body, verify the Ed25519
// signature against the pinned key, check key_id + validity, and (on success)
// persist it to NVS. Returns true iff the envelope is now valid & cached.
bool storeEnvelopeFromJson(const String& json);

// Current cached envelope (valid flag tells you if it may be used).
const OfflineEnvelope& getEnvelope();

// Build the exact canonical byte string that the backend signs. Both sides MUST
// agree on this ordering/format. Documented in the README ("Envelope signing").
String envelopeCanonicalMessage(uint32_t offlineCapCents,
                                uint32_t perTxnCapCents,
                                uint64_t validUntilEpoch,
                                const String& keyId,
                                const String& deviceId);

// Sum of price_cents across all un-reconciled offline records (cumulative spend).
uint32_t pendingSpentCents();

// Number of un-reconciled offline records currently stored.
size_t pendingCount();

// Decide whether an offline charge of `priceCents` is permitted right now:
//   - a valid, unexpired envelope exists,
//   - priceCents <= per_txn_cap_cents,
//   - pendingSpentCents() + priceCents <= offline_cap_cents.
// `reason` is filled with a short human string on failure.
bool canAuthorizeOffline(uint32_t priceCents, uint64_t nowEpoch, String& reason);

// Append a signed offline record to the NVS log. Returns true on success.
bool appendRecord(const OfflineRecord& rec);

// Serialize up to `maxItems` pending records into a reconcile request body:
//   { "batch":[{card_uid, price_cents, client_txn_id, seq, ts}...], "key_id":... }
// Returns the number of records included via `outCount`.
String buildReconcileBatchJson(size_t maxItems, size_t& outCount);

// After the server acknowledges a successful reconcile of the first `count`
// records (FIFO), drop them from the local log.
void pruneAcknowledged(size_t count);

// True if the device HMAC key exists (auto-generated on first boot).
bool hasLogKey();

}  // namespace offline
