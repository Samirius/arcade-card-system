// =============================================================================
// charge_fsm.h  --  Charge state machine (online-first, offline fallback)
// =============================================================================
// Given a card tap + price, decide and execute the charge:
//
//   online  : POST /charge. Approved/Declined drive the UI directly. The server
//             is authoritative; no local balance is trusted.
//   offline : if the network is down, check the signed envelope caps; if within
//             caps, authorize locally, append a signed record to NVS, and light
//             the "offline approved" UI. The record is reconciled later.
//
// On (re)connect, tryReconcile() flushes the offline log to POST /reconcile.
// =============================================================================
#pragma once

#include <Arduino.h>
#include "card_reader.h"

namespace fsm {

// Wire in the active device id + play price/sku (from config).
void begin(const String& deviceId, uint32_t playPriceCents, const String& playSku);

// Handle a single card tap end-to-end. Non-blocking-ish; drives UI + storage.
void handleTap(const CardTap& tap);

// Attempt to refresh the offline envelope from the server (call when online).
// Returns true if a valid envelope is now cached.
bool refreshEnvelope();

// Flush pending offline records to /reconcile if online. Returns records synced.
size_t tryReconcile();

// Best-effort wall-clock (unix seconds). 0 if time is not yet known. Used for
// envelope expiry checks + record timestamps. main.cpp seeds this via SNTP.
uint64_t nowEpoch();
void setClockSynced(bool synced);

}  // namespace fsm
