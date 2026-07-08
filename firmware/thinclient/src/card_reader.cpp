// =============================================================================
// card_reader.cpp  --  PN532 backend + stub backend
// =============================================================================
#include "card_reader.h"
#include "config.h"

// -----------------------------------------------------------------------------
// PN532 wiring (I2C mode). See README for the full wiring table.
//   PN532 SDA -> GPIO21, SCL -> GPIO22, IRQ -> GPIO16, RSTO -> GPIO17
// (SPI mode is also possible; I2C chosen so SPI stays free for a TFT.)
// -----------------------------------------------------------------------------
#define PN532_IRQ   16
#define PN532_RESET 17

static String uidToHex(const uint8_t* uid, uint8_t len) {
    String s;
    s.reserve(len * 2);
    static const char* H = "0123456789ABCDEF";
    for (uint8_t i = 0; i < len; ++i) {
        s += H[uid[i] >> 4];
        s += H[uid[i] & 0x0F];
    }
    return s;
}

#if USE_PN532_HW
// ============================ Real PN532 backend =============================
#include <Wire.h>
#include <Adafruit_PN532.h>

class Pn532CardReader : public CardReader {
public:
    Pn532CardReader() : _nfc(PN532_IRQ, PN532_RESET) {}

    bool begin() override {
        Wire.begin();
        _nfc.begin();
        uint32_t ver = _nfc.getFirmwareVersion();
        if (!ver) {
            Serial.println(F("[reader] PN532 not found"));
            return false;
        }
        _nfc.SAMConfig();
        Serial.printf("[reader] PN532 fw 0x%08X\n", ver);
        return true;
    }

    bool poll(CardTap& tap) override {
        uint8_t uid[7] = {0};
        uint8_t uidLen = 0;
        // 50 ms timeout keeps the main loop responsive.
        bool found = _nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A,
                                              uid, &uidLen, 50);
        if (!found || uidLen == 0) return false;

        String hex = uidToHex(uid, uidLen);
        if (hex == _lastUid) return false;  // debounce same card
        _lastUid = hex;

        tap.uid = hex;
        // DESFire AES auth intentionally not attempted here (see header TODO).
        tap.authenticated = authenticateDesfire(tap);
        return true;
    }

    const char* name() const override { return "PN532(I2C,UID-only)"; }

private:
    Adafruit_PN532 _nfc;
    String _lastUid;
};

static Pn532CardReader g_reader;

#else
// ================================ Stub backend ===============================
// Returns a fixed fake UID the first time poll() is called after a reset of the
// debounce window. Lets the online/offline logic run end-to-end with no NFC HW.
class StubCardReader : public CardReader {
public:
    bool begin() override {
        Serial.println(F("[reader] STUB card reader (no NFC hardware)"));
        return true;
    }

    bool poll(CardTap& tap) override {
        // Emit one synthetic tap roughly every 10 s so a bench run without
        // hardware still exercises the charge path.
        uint32_t now = millis();
        if (now - _lastEmit < 10000UL) return false;
        _lastEmit = now;

        tap.uid = "04DEADBEEF0102";   // fake ISO14443A UID
        tap.authenticated = false;     // stub cannot prove authenticity
        return true;
    }

    const char* name() const override { return "STUB(fake-uid)"; }

private:
    uint32_t _lastEmit = 0;
};

static StubCardReader g_reader;

#endif  // USE_PN532_HW

CardReader& cardReader() { return g_reader; }
