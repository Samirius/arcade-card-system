// =============================================================================
// ids.cpp
// =============================================================================
#include "ids.h"
#include "config.h"
#include <Preferences.h>
#include <esp_system.h>   // esp_random()

namespace {
constexpr const char* kSeqKey = "seq";
uint32_t g_seqCache = 0;

void fillRandom(uint8_t* buf, size_t len) {
    // esp_random() returns a hardware-RNG 32-bit word. Valid once RF (WiFi/BT)
    // is active OR the bootloader RNG seed is present; adequate for nonces/UUIDs.
    size_t i = 0;
    while (i < len) {
        uint32_t r = esp_random();
        for (int b = 0; b < 4 && i < len; ++b, ++i) {
            buf[i] = (uint8_t)(r & 0xFF);
            r >>= 8;
        }
    }
}

char hexNibble(uint8_t v) { return v < 10 ? char('0' + v) : char('a' + (v - 10)); }
}  // namespace

namespace ids {

void begin() {
    Preferences p;
    p.begin(TC_NVS_LOG_NS, /*readOnly=*/true);
    g_seqCache = p.isKey(kSeqKey) ? p.getUInt(kSeqKey, 0) : 0;
    p.end();
}

uint32_t currentSeq() { return g_seqCache; }

uint32_t nextSeq() {
    g_seqCache += 1;
    Preferences p;
    if (p.begin(TC_NVS_LOG_NS, /*readOnly=*/false)) {
        p.putUInt(kSeqKey, g_seqCache);
        p.end();
    } else {
        Serial.println(F("[ids] WARN: failed to persist seq -- ordering at risk"));
    }
    return g_seqCache;
}

String uuidv4() {
    uint8_t b[16];
    fillRandom(b, sizeof(b));
    // Set RFC-4122 version (4) and variant (10xx) bits.
    b[6] = (uint8_t)((b[6] & 0x0F) | 0x40);
    b[8] = (uint8_t)((b[8] & 0x3F) | 0x80);

    char out[37];
    int pos = 0;
    for (int i = 0; i < 16; ++i) {
        if (i == 4 || i == 6 || i == 8 || i == 10) out[pos++] = '-';
        out[pos++] = hexNibble(b[i] >> 4);
        out[pos++] = hexNibble(b[i] & 0x0F);
    }
    out[pos] = '\0';
    return String(out);
}

String nonceHex(size_t bytes) {
    if (bytes == 0) bytes = 16;
    uint8_t* buf = (uint8_t*)malloc(bytes);
    if (!buf) return String();
    fillRandom(buf, bytes);
    String s;
    s.reserve(bytes * 2);
    for (size_t i = 0; i < bytes; ++i) {
        s += hexNibble(buf[i] >> 4);
        s += hexNibble(buf[i] & 0x0F);
    }
    free(buf);
    return s;
}

}  // namespace ids
