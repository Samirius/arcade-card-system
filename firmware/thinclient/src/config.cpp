// =============================================================================
// config.cpp  --  NVS-backed configuration loader
// =============================================================================
#include "config.h"
#include <Preferences.h>
#include <string.h>

static String nvsGet(Preferences& p, const char* key, const char* fallback) {
    if (p.isKey(key)) {
        return p.getString(key, fallback);
    }
    return String(fallback);
}

void configLoad(DeviceConfig& out) {
    Preferences p;
    // read-only open; if the namespace does not exist yet we still get defaults.
    p.begin(TC_NVS_CFG_NS, /*readOnly=*/true);

    out.wifiSsid       = nvsGet(p, "wifi_ssid", DEFAULT_WIFI_SSID);
    out.wifiPassword   = nvsGet(p, "wifi_pass", DEFAULT_WIFI_PASSWORD);
    out.baseUrl        = nvsGet(p, "base_url",  DEFAULT_BASE_URL);
    out.deviceId       = nvsGet(p, "device_id", DEFAULT_DEVICE_ID);
    out.deviceToken    = nvsGet(p, "dev_token", DEFAULT_DEVICE_TOKEN);
    out.playPriceCents = p.isKey("price_cents")
                             ? p.getUInt("price_cents", DEFAULT_PLAY_PRICE_CENTS)
                             : (uint32_t)DEFAULT_PLAY_PRICE_CENTS;
    out.playSku        = nvsGet(p, "play_sku", DEFAULT_PLAY_SKU);

    p.end();
}

bool configSetString(const char* key, const String& value) {
    Preferences p;
    if (!p.begin(TC_NVS_CFG_NS, /*readOnly=*/false)) {
        return false;
    }
    size_t n = p.putString(key, value);
    p.end();
    return n == value.length();
}

bool configHasPinnedCA() {
    // Placeholder marker check -- treat the shipped stub as "no pinned CA".
    return strstr(TC_SERVER_ROOT_CA_PEM, "REPLACE_WITH_PINNED_SERVER_ROOT_CA") == nullptr;
}
