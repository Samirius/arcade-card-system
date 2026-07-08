// =============================================================================
// ids.h  --  Identifier generation for the charge contract
// =============================================================================
//   client_txn_id : UUIDv4 string. Stable per logical transaction so the
//                   backend can dedupe retries idempotently. Generated ONCE
//                   when a charge is first attempted and reused across retries
//                   and across the offline->reconcile handoff.
//   nonce         : per-request random hex, replay-defense on each POST.
//   seq           : monotonically increasing counter persisted in NVS. Used to
//                   order offline records inside a reconcile batch and to make
//                   the local log tamper-evident together with the HMAC.
// =============================================================================
#pragma once

#include <Arduino.h>

namespace ids {

// Initialize the persistent monotonic sequence from NVS (call once in setup()).
void begin();

// Return the next monotonic sequence number and persist it. Never returns the
// same value twice across reboots (barring NVS failure, which is logged).
uint32_t nextSeq();

// Peek the current seq without incrementing.
uint32_t currentSeq();

// Generate a RFC-4122 v4 UUID string, e.g. "3f2504e0-4f89-41d3-9a0c-0305e82c3301".
// Uses the ESP32 hardware RNG (esp_random) which is seeded from RF/thermal noise.
String uuidv4();

// Generate a random hex nonce of `bytes` bytes (default 16 -> 32 hex chars).
String nonceHex(size_t bytes = 16);

}  // namespace ids
