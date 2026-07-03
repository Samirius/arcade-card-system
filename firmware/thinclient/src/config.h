// =============================================================================
// config.h  --  Compile-time defaults + runtime (NVS) configuration schema
// =============================================================================
//
// Configuration precedence at runtime:
//   1. Values stored in NVS (namespace "tc-cfg") -- provisioned per device.
//   2. The compile-time DEFAULT_* fallbacks below (dev/bench convenience only).
//
// SECURITY: The DEFAULT_DEVICE_TOKEN and DEFAULT_* WiFi creds below are
// placeholders for bench bring-up ONLY. Production devices MUST be provisioned
// with a unique device token (or, better, an mTLS client cert -- see README)
// written to NVS, never a shared compile-time secret.
// =============================================================================
#pragma once

#include <Arduino.h>

// ---- Firmware identity -----------------------------------------------------
#define TC_FIRMWARE_NAME     "arcade-thinclient"
#define TC_FIRMWARE_VERSION  "0.1.0-scaffold"

// ---- NVS namespaces --------------------------------------------------------
#define TC_NVS_CFG_NS        "tc-cfg"    // provisioned config
#define TC_NVS_LOG_NS        "tc-log"    // offline transaction log + seq
#define TC_NVS_ENV_NS        "tc-env"    // cached offline envelope

// ---- Bench/dev defaults (OVERRIDE via NVS in production) --------------------
#define DEFAULT_WIFI_SSID        "YOUR_WIFI_SSID"
#define DEFAULT_WIFI_PASSWORD    "YOUR_WIFI_PASSWORD"

// Cloud base URL. MUST be https:// for the money path.
#define DEFAULT_BASE_URL         "https://api.arcade.example.com"

// Logical device id, used in the offline-envelope path + reconcile batch.
#define DEFAULT_DEVICE_ID        "DEVICE-0001"

// Pilot device bearer token (Authorization: Bearer <device_token>).
// Placeholder -- replace per device via NVS. mTLS/X.509 is the documented
// production upgrade (see README "Auth model").
#define DEFAULT_DEVICE_TOKEN     "REPLACE_WITH_PROVISIONED_DEVICE_TOKEN"

// ---- Product / pricing defaults --------------------------------------------
// A real deployment reads price/sku from the attached machine (GPIO/serial) or
// a local product table. For the scaffold, one fixed "play" price is used.
#define DEFAULT_PLAY_PRICE_CENTS 100        // $1.00
#define DEFAULT_PLAY_SKU         "PLAY-1CR"

// ---- Timeouts / retry ------------------------------------------------------
#define TC_WIFI_CONNECT_TIMEOUT_MS   15000UL
#define TC_HTTP_TIMEOUT_MS           8000UL   // charge round-trip budget
#define TC_HTTP_MAX_RETRIES          2        // idempotent via client_txn_id
#define TC_CARD_DEBOUNCE_MS          2000UL

// -----------------------------------------------------------------------------
// Pinned Ed25519 PUBLIC KEY (32 raw bytes) used to verify the offline envelope
// signature. Provisioned into every device; the matching private key lives ONLY
// on the backend signer.
//
// THIS IS A PLACEHOLDER (all-zero) key. With an all-zero key, envelope
// verification will (correctly) FAIL for any real signature -- the device will
// refuse to run offline until a real key is pinned. Replace both the bytes here
// and the `key_id` the backend advertises.
// -----------------------------------------------------------------------------
static const uint8_t TC_ENVELOPE_PUBKEY[32] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
// The key_id the backend uses for the above public key. The device only trusts
// envelopes whose key_id matches this pin (defense against key confusion).
#define TC_ENVELOPE_KEY_ID   "ed25519-pilot-0"

// -----------------------------------------------------------------------------
// Pinned server root CA (PEM). Replace with the actual issuing root/intermediate
// for api.arcade.example.com. When empty AND THINCLIENT_ALLOW_INSECURE_TLS=1,
// the client falls back to setInsecure() for bench use only.
// -----------------------------------------------------------------------------
static const char TC_SERVER_ROOT_CA_PEM[] = R"PEM(
-----BEGIN CERTIFICATE-----
REPLACE_WITH_PINNED_SERVER_ROOT_CA
-----END CERTIFICATE-----
)PEM";

// Runtime configuration, loaded from NVS with the above as fallbacks.
struct DeviceConfig {
    String wifiSsid;
    String wifiPassword;
    String baseUrl;
    String deviceId;
    String deviceToken;
    uint32_t playPriceCents;
    String playSku;
};

// Load configuration from NVS, falling back to compile-time defaults.
void configLoad(DeviceConfig& out);

// Persist a single string key into the config namespace (used by a future
// provisioning path / serial console). Returns true on success.
bool configSetString(const char* key, const String& value);

// True if the server root CA looks like a real pinned cert (not the placeholder).
bool configHasPinnedCA();
