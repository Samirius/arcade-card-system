// =============================================================================
// main.cpp  --  Arcade Card System :: server-authoritative THIN CLIENT reader
// =============================================================================
// Boot sequence:
//   1. Load config (NVS -> compile-time defaults).
//   2. Init IDs (monotonic seq), offline store (verify cached envelope + HMAC
//      key), card reader, UI.
//   3. Connect WiFi (best-effort), sync SNTP clock, fetch+verify offline
//      envelope, flush any pending reconcile batch.
//   4. Loop: poll reader -> charge_fsm.handleTap(); periodically retry
//      connectivity + reconcile.
//
// Design contract with the backend (see README):
//   POST /api/v1/charge, GET /api/v1/devices/{id}/offline-envelope,
//   POST /api/v1/reconcile, all with Authorization: Bearer <device_token>.
// =============================================================================
#include <Arduino.h>
#include <WiFi.h>
#include <time.h>

#include "config.h"
#include "ids.h"
#include "ui.h"
#include "card_reader.h"
#include "net_client.h"
#include "offline_store.h"
#include "charge_fsm.h"

// Active device id -- referenced by offline_store.cpp (envelope canonical msg).
String g_deviceId;

static DeviceConfig g_cfg;
static uint32_t s_lastConnectTry = 0;
static uint32_t s_lastReconcile  = 0;

static const char* NTP_SERVER_1 = "pool.ntp.org";
static const char* NTP_SERVER_2 = "time.google.com";

// Attempt SNTP time sync (needed for envelope expiry + record timestamps).
static void syncClock() {
    if (!net::wifiConnected()) return;
    configTime(0, 0, NTP_SERVER_1, NTP_SERVER_2);  // UTC
    // brief wait for first sync
    for (int i = 0; i < 20; ++i) {
        if (time(nullptr) > 1700000000) break;
        delay(100);
    }
    bool synced = time(nullptr) > 1700000000;
    fsm::setClockSynced(synced);
    Serial.printf("[main] clock %s (epoch=%ld)\n",
                  synced ? "synced" : "NOT synced", (long)time(nullptr));
}

// One-time online bring-up: clock, envelope, reconcile.
static void onlineBringup() {
    syncClock();
    if (fsm::refreshEnvelope()) {
        Serial.println(F("[main] offline envelope cached & verified"));
    } else {
        Serial.println(F("[main] no valid offline envelope (offline play disabled)"));
    }
    fsm::tryReconcile();
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println();
    Serial.println(F("======================================================"));
    Serial.printf ("  %s %s\n", TC_FIRMWARE_NAME, TC_FIRMWARE_VERSION);
    Serial.println(F("  server-authoritative thin client (online + offline)"));
    Serial.println(F("======================================================"));

    ui::begin();

    configLoad(g_cfg);
    g_deviceId = g_cfg.deviceId;
    Serial.printf("[main] device_id=%s base_url=%s price=%uc sku=%s\n",
                  g_cfg.deviceId.c_str(), g_cfg.baseUrl.c_str(),
                  g_cfg.playPriceCents, g_cfg.playSku.c_str());

    if (g_cfg.deviceToken == DEFAULT_DEVICE_TOKEN)
        Serial.println(F("[main] WARNING: using placeholder device token -- provision NVS!"));
    if (!configHasPinnedCA())
        Serial.println(F("[main] WARNING: no pinned server CA -- bench TLS only"));

    ids::begin();
    offline::begin();     // re-verifies any cached envelope against pinned key
    net::begin(g_cfg);

    if (!cardReader().begin())
        Serial.println(F("[main] card reader init failed (continuing)"));
    Serial.printf("[main] card reader: %s\n", cardReader().name());

    fsm::begin(g_cfg.deviceId, g_cfg.playPriceCents, g_cfg.playSku);

    Serial.printf("[main] pending offline records: %u, spent=%uc\n",
                  (unsigned)offline::pendingCount(), offline::pendingSpentCents());

    // Best-effort connect + bring-up. Device is fully functional offline if this
    // fails, as long as a valid envelope was previously cached.
    if (net::wifiConnect()) {
        onlineBringup();
    }

    ui::setState(UiState::Idle);
    ui::showLines("Ready", net::wifiConnected() ? "online" : "offline");
}

void loop() {
    ui::tick();

    // 1) Card handling.
    CardTap tap;
    if (cardReader().poll(tap)) {
        fsm::handleTap(tap);
        // Return to idle after a short dwell so the operator sees the result.
        delay(1200);
        ui::setState(UiState::Idle);
        ui::showLines("Ready", net::wifiConnected() ? "online" : "offline");
    }

    // 2) Periodic connectivity recovery + reconcile (every ~15 s when offline,
    //    and opportunistic reconcile every ~30 s when online with a backlog).
    uint32_t now = millis();
    if (!net::wifiConnected() && now - s_lastConnectTry > 15000) {
        s_lastConnectTry = now;
        if (net::wifiConnect()) {
            onlineBringup();  // resync clock, refresh envelope, flush backlog
        }
    } else if (net::wifiConnected() && offline::pendingCount() > 0 &&
               now - s_lastReconcile > 30000) {
        s_lastReconcile = now;
        fsm::tryReconcile();
    }

    delay(20);
}
