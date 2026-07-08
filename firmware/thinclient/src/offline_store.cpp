// =============================================================================
// offline_store.cpp
// =============================================================================
#include "offline_store.h"
#include "config.h"
#include "crypto_ed25519.h"

#include <ArduinoJson.h>
#include <Preferences.h>
#include <esp_system.h>
#include <mbedtls/base64.h>
#include <mbedtls/md.h>
#include <string.h>

// The active device id is needed inside the canonical message. main.cpp sets it.
extern String g_deviceId;

namespace {

OfflineEnvelope g_env;

// NVS keys.
constexpr const char* kEnvJson   = "env_json";   // last raw envelope body
constexpr const char* kLogCount  = "log_n";      // number of records
constexpr const char* kLogKey    = "log_hmac_k"; // device-local HMAC key (32B)
// records stored as rec0000.. JSON strings
String recKey(size_t i) { char b[12]; snprintf(b, sizeof(b), "rec%04u", (unsigned)i); return String(b); }

// ---- helpers ---------------------------------------------------------------

// Decode a signature that may be base64 (with/without padding) or hex into raw
// bytes. Returns decoded length, or 0 on failure. `out` must hold >=64 bytes.
size_t decodeSignature(const String& sig, uint8_t* out, size_t outCap) {
    // Try hex first if it looks like 128 hex chars.
    bool looksHex = (sig.length() == 128);
    if (looksHex) {
        for (size_t i = 0; i < sig.length(); ++i) {
            char c = sig[i];
            if (!isxdigit((int)c)) { looksHex = false; break; }
        }
    }
    if (looksHex) {
        auto nib = [](char c) -> int {
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            if (c >= 'A' && c <= 'F') return c - 'A' + 10;
            return -1;
        };
        size_t n = sig.length() / 2;
        if (n > outCap) return 0;
        for (size_t i = 0; i < n; ++i) {
            int hi = nib(sig[2 * i]), lo = nib(sig[2 * i + 1]);
            if (hi < 0 || lo < 0) return 0;
            out[i] = (uint8_t)((hi << 4) | lo);
        }
        return n;
    }
    // Otherwise base64 (standard alphabet).
    size_t olen = 0;
    int rc = mbedtls_base64_decode(out, outCap, &olen,
                                   (const unsigned char*)sig.c_str(),
                                   sig.length());
    if (rc != 0) return 0;
    return olen;
}

// Load or create the device-local HMAC key used to tamper-protect log records.
bool loadOrCreateLogKey(uint8_t key[32]) {
    Preferences p;
    p.begin(TC_NVS_LOG_NS, /*readOnly=*/false);
    size_t have = p.isKey(kLogKey) ? p.getBytesLength(kLogKey) : 0;
    if (have == 32) {
        p.getBytes(kLogKey, key, 32);
        p.end();
        return true;
    }
    // generate a fresh key from the HW RNG
    for (int i = 0; i < 32; i += 4) {
        uint32_t r = esp_random();
        memcpy(key + i, &r, 4);
    }
    bool ok = p.putBytes(kLogKey, key, 32) == 32;
    p.end();
    return ok;
}

// Compute HMAC-SHA256(key, msg) -> 32 bytes.
bool hmacSha256(const uint8_t key[32], const String& msg, uint8_t out[32]) {
    const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    if (!info) return false;
    int rc = mbedtls_md_hmac(info, key, 32,
                             (const unsigned char*)msg.c_str(), msg.length(),
                             out);
    return rc == 0;
}

String toHex(const uint8_t* b, size_t n) {
    static const char* H = "0123456789abcdef";
    String s; s.reserve(n * 2);
    for (size_t i = 0; i < n; ++i) { s += H[b[i] >> 4]; s += H[b[i] & 0xF]; }
    return s;
}

// The canonical string over which a record's HMAC is computed.
String recordCanonical(const OfflineRecord& r) {
    // pipe-delimited, fixed field order
    String s;
    s.reserve(96);
    s += r.cardUid; s += '|';
    s += String(r.priceCents); s += '|';
    s += r.clientTxnId; s += '|';
    s += String(r.seq); s += '|';
    s += String((uint32_t)r.ts);
    return s;
}

size_t logCount() {
    Preferences p;
    p.begin(TC_NVS_LOG_NS, /*readOnly=*/true);
    size_t n = p.isKey(kLogCount) ? p.getUInt(kLogCount, 0) : 0;
    p.end();
    return n;
}

}  // namespace

namespace offline {

String envelopeCanonicalMessage(uint32_t offlineCapCents,
                                uint32_t perTxnCapCents,
                                uint64_t validUntilEpoch,
                                const String& keyId,
                                const String& deviceId) {
    // CANONICAL FORMAT (backend MUST sign exactly this):
    //   "v1|<device_id>|<offline_cap_cents>|<per_txn_cap_cents>|<valid_until>|<key_id>"
    // valid_until is unix seconds. No trailing newline. UTF-8.
    String s;
    s.reserve(96);
    s += "v1|";
    s += deviceId; s += '|';
    s += String(offlineCapCents); s += '|';
    s += String(perTxnCapCents); s += '|';
    s += String((uint32_t)validUntilEpoch); s += '|';
    s += keyId;
    return s;
}

void begin() {
    g_env = OfflineEnvelope{};
    Preferences p;
    p.begin(TC_NVS_ENV_NS, /*readOnly=*/true);
    String cached = p.isKey(kEnvJson) ? p.getString(kEnvJson, "") : "";
    p.end();
    if (cached.length()) {
        // Re-verify on load; do NOT trust a cached envelope blindly.
        storeEnvelopeFromJson(cached);
    }
    // Ensure a log HMAC key exists.
    uint8_t k[32];
    loadOrCreateLogKey(k);
}

bool hasLogKey() {
    Preferences p;
    p.begin(TC_NVS_LOG_NS, /*readOnly=*/true);
    bool ok = p.isKey(kLogKey) && p.getBytesLength(kLogKey) == 32;
    p.end();
    return ok;
}

const OfflineEnvelope& getEnvelope() { return g_env; }

bool storeEnvelopeFromJson(const String& json) {
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, json);
    if (err) {
        Serial.printf("[offline] envelope parse error: %s\n", err.c_str());
        return false;
    }

    OfflineEnvelope e;
    e.offlineCapCents = doc["offline_cap_cents"] | 0u;
    e.perTxnCapCents  = doc["per_txn_cap_cents"] | 0u;
    e.validUntilEpoch = (uint64_t)(doc["valid_until"] | 0ULL);
    e.keyId           = String((const char*)(doc["key_id"] | ""));
    String signature  = String((const char*)(doc["signature"] | ""));

    // 1) key_id must match our pinned key (reject key confusion).
    if (e.keyId != TC_ENVELOPE_KEY_ID) {
        Serial.printf("[offline] envelope key_id '%s' != pinned '%s'\n",
                      e.keyId.c_str(), TC_ENVELOPE_KEY_ID);
        return false;
    }

    // 2) decode + verify Ed25519 signature over the canonical message.
    uint8_t sig[64];
    size_t sigLen = decodeSignature(signature, sig, sizeof(sig));
    if (sigLen != 64) {
        Serial.printf("[offline] bad signature length (%u)\n", (unsigned)sigLen);
        return false;
    }

    String msg = envelopeCanonicalMessage(e.offlineCapCents, e.perTxnCapCents,
                                          e.validUntilEpoch, e.keyId, g_deviceId);
    bool ok = tccrypto::ed25519Verify((const uint8_t*)msg.c_str(), msg.length(),
                                      sig, TC_ENVELOPE_PUBKEY);
    if (!ok) {
        Serial.println(F("[offline] envelope signature INVALID -- rejected"));
        if (!tccrypto::ed25519Available()) {
            Serial.println(F("[offline] (crypto backend is the fail-closed stub)"));
        }
        return false;
    }

    e.valid = true;
    g_env = e;

    // 3) persist verified envelope for use across reboots / brownouts.
    Preferences p;
    if (p.begin(TC_NVS_ENV_NS, /*readOnly=*/false)) {
        p.putString(kEnvJson, json);
        p.end();
    }
    Serial.printf("[offline] envelope OK: per_txn=%u offline_cap=%u valid_until=%u\n",
                  e.perTxnCapCents, e.offlineCapCents, (unsigned)e.validUntilEpoch);
    return true;
}

size_t pendingCount() { return logCount(); }

uint32_t pendingSpentCents() {
    size_t n = logCount();
    if (n == 0) return 0;
    Preferences p;
    p.begin(TC_NVS_LOG_NS, /*readOnly=*/true);
    uint32_t total = 0;
    StaticJsonDocument<256> doc;
    for (size_t i = 0; i < n; ++i) {
        String s = p.getString(recKey(i).c_str(), "");
        if (!s.length()) continue;
        doc.clear();
        if (deserializeJson(doc, s)) continue;
        total += (uint32_t)(doc["price_cents"] | 0u);
    }
    p.end();
    return total;
}

bool canAuthorizeOffline(uint32_t priceCents, uint64_t nowEpoch, String& reason) {
    if (!g_env.valid) { reason = "no valid envelope"; return false; }
    if (g_env.validUntilEpoch != 0 && nowEpoch != 0 &&
        nowEpoch > g_env.validUntilEpoch) {
        reason = "envelope expired";
        return false;
    }
    if (g_env.perTxnCapCents && priceCents > g_env.perTxnCapCents) {
        reason = "over per-txn cap";
        return false;
    }
    uint32_t spent = pendingSpentCents();
    if (g_env.offlineCapCents &&
        (uint64_t)spent + priceCents > g_env.offlineCapCents) {
        reason = "over offline cap";
        return false;
    }
    return true;
}

bool appendRecord(const OfflineRecord& rec) {
    uint8_t key[32];
    if (!loadOrCreateLogKey(key)) {
        Serial.println(F("[offline] cannot load HMAC key"));
        return false;
    }
    uint8_t tag[32];
    if (!hmacSha256(key, recordCanonical(rec), tag)) return false;

    StaticJsonDocument<256> doc;
    doc["card_uid"]      = rec.cardUid;
    doc["price_cents"]   = rec.priceCents;
    doc["client_txn_id"] = rec.clientTxnId;
    doc["seq"]           = rec.seq;
    doc["ts"]            = (uint32_t)rec.ts;
    doc["hmac"]          = toHex(tag, sizeof(tag));

    String out;
    serializeJson(doc, out);

    Preferences p;
    if (!p.begin(TC_NVS_LOG_NS, /*readOnly=*/false)) return false;
    size_t n = p.isKey(kLogCount) ? p.getUInt(kLogCount, 0) : 0;
    bool ok = p.putString(recKey(n).c_str(), out) == out.length();
    if (ok) p.putUInt(kLogCount, n + 1);
    p.end();
    if (ok) {
        Serial.printf("[offline] appended record #%u (%s $%u.%02u)\n",
                      (unsigned)n, rec.cardUid.c_str(),
                      rec.priceCents / 100, rec.priceCents % 100);
    }
    return ok;
}

String buildReconcileBatchJson(size_t maxItems, size_t& outCount) {
    outCount = 0;
    size_t n = logCount();
    if (n == 0) return String();

    DynamicJsonDocument doc(4096);
    JsonArray batch = doc.createNestedArray("batch");

    Preferences p;
    p.begin(TC_NVS_LOG_NS, /*readOnly=*/true);
    StaticJsonDocument<256> rec;
    for (size_t i = 0; i < n && outCount < maxItems; ++i) {
        String s = p.getString(recKey(i).c_str(), "");
        if (!s.length()) continue;
        rec.clear();
        if (deserializeJson(rec, s)) continue;
        JsonObject o = batch.createNestedObject();
        o["card_uid"]      = rec["card_uid"];
        o["price_cents"]   = rec["price_cents"];
        o["client_txn_id"] = rec["client_txn_id"];
        o["seq"]           = rec["seq"];
        o["ts"]            = rec["ts"];
        outCount++;
    }
    p.end();

    doc["key_id"] = TC_ENVELOPE_KEY_ID;

    String out;
    serializeJson(doc, out);
    return out;
}

void pruneAcknowledged(size_t count) {
    size_t n = logCount();
    if (count == 0 || n == 0) return;
    if (count > n) count = n;

    Preferences p;
    if (!p.begin(TC_NVS_LOG_NS, /*readOnly=*/false)) return;

    // FIFO: shift records [count..n) down to [0..n-count), then drop the tail.
    size_t remaining = n - count;
    for (size_t i = 0; i < remaining; ++i) {
        String s = p.getString(recKey(i + count).c_str(), "");
        p.putString(recKey(i).c_str(), s);
    }
    for (size_t i = remaining; i < n; ++i) {
        p.remove(recKey(i).c_str());
    }
    p.putUInt(kLogCount, remaining);
    p.end();
    Serial.printf("[offline] pruned %u reconciled records, %u remain\n",
                  (unsigned)count, (unsigned)remaining);
}

}  // namespace offline
