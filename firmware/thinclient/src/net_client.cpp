// =============================================================================
// net_client.cpp
// =============================================================================
#include "net_client.h"
#include "ids.h"

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

namespace {
DeviceConfig g_cfg;

// Configure TLS trust on a fresh secure client. Pins the root CA when one is
// provisioned; otherwise (bench only, guarded) falls back to insecure.
void applyTls(WiFiClientSecure& client) {
    if (configHasPinnedCA()) {
        client.setCACert(TC_SERVER_ROOT_CA_PEM);
    } else {
#if THINCLIENT_ALLOW_INSECURE_TLS
        Serial.println(F("[net] WARNING: no pinned CA -> setInsecure() (BENCH ONLY)"));
        client.setInsecure();
#else
        // Fail closed: with no pinned CA and insecure disallowed, the handshake
        // will fail, which is the intended behaviour for production builds.
        Serial.println(F("[net] ERROR: no pinned CA and insecure TLS disabled"));
#endif
    }
    // mTLS/X.509 client-cert upgrade would set client.setCertificate()/
    // setPrivateKey() here (see README "Auth model").
}

void addAuth(HTTPClient& http) {
    http.addHeader("Authorization", String("Bearer ") + g_cfg.deviceToken);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Id", g_cfg.deviceId);
}
}  // namespace

namespace net {

void begin(const DeviceConfig& cfg) { g_cfg = cfg; }

bool wifiConnected() { return WiFi.status() == WL_CONNECTED; }

bool wifiConnect() {
    if (wifiConnected()) return true;
    Serial.printf("[net] WiFi connecting to '%s'\n", g_cfg.wifiSsid.c_str());
    WiFi.mode(WIFI_STA);
    WiFi.begin(g_cfg.wifiSsid.c_str(), g_cfg.wifiPassword.c_str());
    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED &&
           millis() - start < TC_WIFI_CONNECT_TIMEOUT_MS) {
        delay(250);
    }
    bool ok = wifiConnected();
    if (ok) Serial.printf("[net] WiFi up, ip=%s\n", WiFi.localIP().toString().c_str());
    else    Serial.println(F("[net] WiFi connect timeout -> offline mode"));
    return ok;
}

ChargeOutcome charge(const String& cardUid, uint32_t priceCents,
                     const String& sku, const String& clientTxnId,
                     uint64_t tsEpoch) {
    ChargeOutcome out;
    if (!wifiConnected()) { out.status = ChargeOutcome::NetworkError; return out; }

    String url = g_cfg.baseUrl + "/api/v1/charge";

    for (int attempt = 0; attempt <= TC_HTTP_MAX_RETRIES; ++attempt) {
        WiFiClientSecure client;
        applyTls(client);
        HTTPClient http;
        http.setTimeout(TC_HTTP_TIMEOUT_MS);
        if (!http.begin(client, url)) {
            out.status = ChargeOutcome::NetworkError;
            continue;
        }
        addAuth(http);

        // Build request body. client_txn_id is STABLE across retries (idempotent);
        // nonce is refreshed each attempt.
        StaticJsonDocument<384> doc;
        doc["card_uid"]      = cardUid;
        doc["price_cents"]   = priceCents;
        doc["sku"]           = sku;
        doc["client_txn_id"] = clientTxnId;
        doc["nonce"]         = ids::nonceHex(16);
        doc["ts"]            = (uint32_t)tsEpoch;
        String body;
        serializeJson(doc, body);

        int code = http.POST(body);
        out.httpCode = code;

        if (code <= 0) {
            Serial.printf("[net] charge transport err %d (attempt %d)\n", code, attempt);
            http.end();
            out.status = ChargeOutcome::NetworkError;
            delay(200 * (attempt + 1));
            continue;  // retry with same client_txn_id
        }

        String resp = http.getString();
        http.end();
        out.rawBody = resp;

        if (code < 200 || code >= 300) {
            // 5xx -> retry; 4xx -> treat as protocol error (don't hammer).
            if (code >= 500) { out.status = ChargeOutcome::NetworkError; delay(200); continue; }
            out.status = ChargeOutcome::ProtocolError;
            return out;
        }

        StaticJsonDocument<384> rdoc;
        if (deserializeJson(rdoc, resp)) {
            out.status = ChargeOutcome::ProtocolError;
            return out;
        }
        const char* result = rdoc["result"] | "";
        out.balanceAfterCents = (int64_t)(rdoc["balance_after_cents"] | -1);
        out.serverTxnId = String((const char*)(rdoc["server_txn_id"] | ""));

        if (strcmp(result, "approved") == 0)      out.status = ChargeOutcome::Approved;
        else if (strcmp(result, "declined") == 0) out.status = ChargeOutcome::Declined;
        else                                        out.status = ChargeOutcome::ProtocolError;
        return out;
    }
    return out;  // exhausted retries -> NetworkError
}

int fetchOfflineEnvelope(String& outBody) {
    outBody = "";
    if (!wifiConnected()) return -1;

    String url = g_cfg.baseUrl + "/api/v1/devices/" + g_cfg.deviceId + "/offline-envelope";
    WiFiClientSecure client;
    applyTls(client);
    HTTPClient http;
    http.setTimeout(TC_HTTP_TIMEOUT_MS);
    if (!http.begin(client, url)) return -1;
    addAuth(http);

    int code = http.GET();
    if (code == 200) outBody = http.getString();
    http.end();
    return code;
}

int reconcile(const String& batchJson, String& outBody) {
    outBody = "";
    if (!wifiConnected()) return -1;

    String url = g_cfg.baseUrl + "/api/v1/reconcile";
    WiFiClientSecure client;
    applyTls(client);
    HTTPClient http;
    http.setTimeout(TC_HTTP_TIMEOUT_MS);
    if (!http.begin(client, url)) return -1;
    addAuth(http);

    int code = http.POST(batchJson);
    outBody = http.getString();
    http.end();
    return code;
}

}  // namespace net
