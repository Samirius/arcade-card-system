// =============================================================================
// charge_fsm.cpp
// =============================================================================
#include "charge_fsm.h"
#include "net_client.h"
#include "offline_store.h"
#include "ids.h"
#include "ui.h"
#include "config.h"

#include <time.h>

namespace {
String   g_deviceIdLocal;
uint32_t g_priceCents = DEFAULT_PLAY_PRICE_CENTS;
String   g_sku = DEFAULT_PLAY_SKU;
bool     g_clockSynced = false;

String centsToDollars(int64_t c) {
    if (c < 0) return String("?");
    char b[24];
    snprintf(b, sizeof(b), "$%lld.%02lld", (long long)(c / 100), (long long)(c % 100));
    return String(b);
}
}  // namespace

namespace fsm {

void begin(const String& deviceId, uint32_t playPriceCents, const String& playSku) {
    g_deviceIdLocal = deviceId;
    g_priceCents = playPriceCents;
    g_sku = playSku;
}

void setClockSynced(bool synced) { g_clockSynced = synced; }

uint64_t nowEpoch() {
    if (!g_clockSynced) return 0;
    time_t t = time(nullptr);
    if (t < 1700000000) return 0;  // sanity: before ~2023 means not set
    return (uint64_t)t;
}

bool refreshEnvelope() {
    if (!net::wifiConnected()) return offline::getEnvelope().valid;
    String body;
    int code = net::fetchOfflineEnvelope(body);
    if (code == 200 && body.length()) {
        bool ok = offline::storeEnvelopeFromJson(body);  // verifies signature
        if (!ok) Serial.println(F("[fsm] fetched envelope failed verification"));
        return ok;
    }
    Serial.printf("[fsm] envelope fetch http=%d\n", code);
    return offline::getEnvelope().valid;
}

size_t tryReconcile() {
    if (!net::wifiConnected()) return 0;
    if (offline::pendingCount() == 0) return 0;

    ui::setState(UiState::Syncing);
    size_t totalSynced = 0;
    // Upload in bounded batches until the log drains or the server rejects.
    for (int guard = 0; guard < 32 && offline::pendingCount() > 0; ++guard) {
        size_t count = 0;
        String batch = offline::buildReconcileBatchJson(/*maxItems=*/16, count);
        if (count == 0) break;

        String resp;
        int code = net::reconcile(batch, resp);
        if (code >= 200 && code < 300) {
            offline::pruneAcknowledged(count);  // server accepted -> safe to drop
            totalSynced += count;
        } else {
            Serial.printf("[fsm] reconcile http=%d, will retry later\n", code);
            break;  // keep records; try again on next reconnect
        }
    }
    if (totalSynced) Serial.printf("[fsm] reconciled %u records\n", (unsigned)totalSynced);
    return totalSynced;
}

void handleTap(const CardTap& tap) {
    ui::setState(UiState::Reading);
    ui::showLines("Card", tap.uid + (tap.authenticated ? " (auth)" : " (uid-only)"));

    // Stable idempotency key for THIS logical transaction (survives retries and
    // the offline->reconcile handoff).
    String clientTxnId = ids::uuidv4();
    uint64_t ts = nowEpoch();

    // ------------------------------------------------------------------ ONLINE
    if (net::wifiConnected()) {
        ui::setState(UiState::ChargingOnline);
        ChargeOutcome oc = net::charge(tap.uid, g_priceCents, g_sku, clientTxnId, ts);

        switch (oc.status) {
            case ChargeOutcome::Approved:
                ui::setState(UiState::ApprovedOnline);
                ui::showLines("APPROVED", "Bal " + centsToDollars(oc.balanceAfterCents));
                Serial.printf("[fsm] online approved txn=%s bal=%lld\n",
                              oc.serverTxnId.c_str(), (long long)oc.balanceAfterCents);
                return;

            case ChargeOutcome::Declined:
                ui::setState(UiState::Declined);
                ui::showLines("DECLINED", "Bal " + centsToDollars(oc.balanceAfterCents));
                return;

            case ChargeOutcome::ProtocolError:
                // Server reachable but response unusable -> do NOT silently fall
                // back to offline (we can't tell if the charge applied). Fail safe.
                ui::setState(UiState::Error);
                ui::showLines("ERROR", "protocol");
                Serial.printf("[fsm] protocol error http=%d body=%s\n",
                              oc.httpCode, oc.rawBody.c_str());
                return;

            case ChargeOutcome::NetworkError:
            default:
                // Network dropped mid-flow -> fall through to offline path.
                Serial.println(F("[fsm] charge network error -> trying offline"));
                break;
        }
    }

    // ----------------------------------------------------------------- OFFLINE
    String reason;
    if (!offline::canAuthorizeOffline(g_priceCents, ts, reason)) {
        ui::setState(UiState::OfflineNoCaps);
        ui::showLines("NO OFFLINE", reason);
        Serial.printf("[fsm] offline authorize refused: %s\n", reason.c_str());
        return;
    }

    OfflineRecord rec;
    rec.cardUid     = tap.uid;
    rec.priceCents  = g_priceCents;
    rec.clientTxnId = clientTxnId;
    rec.seq         = ids::nextSeq();
    rec.ts          = ts;

    if (offline::appendRecord(rec)) {
        ui::setState(UiState::ApprovedOffline);
        ui::showLines("OFFLINE OK", "queued seq " + String(rec.seq));
        Serial.printf("[fsm] offline authorized $%u.%02u seq=%u txn=%s\n",
                      g_priceCents / 100, g_priceCents % 100, rec.seq,
                      clientTxnId.c_str());
    } else {
        ui::setState(UiState::Error);
        ui::showLines("ERROR", "log write");
    }
}

}  // namespace fsm
