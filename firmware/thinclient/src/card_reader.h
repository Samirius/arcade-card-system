// =============================================================================
// card_reader.h  --  Contactless card reader interface (PN532 / DESFire)
// =============================================================================
// The reader is abstracted behind CardReader so the charge state machine never
// depends on a concrete NFC chip. Two backends are provided:
//
//   * Pn532CardReader  (USE_PN532_HW=1) -- reads the ISO14443A UID via an
//     Adafruit PN532 over I2C. UID read only.
//   * StubCardReader   (USE_PN532_HW=0, default) -- returns a deterministic
//     fake UID when a virtual "tap" is requested. Lets the money/offline logic
//     be compiled and exercised with no hardware attached.
//
// DESFire EV2/EV3 mutual AES authentication (the part that proves the card is
// genuine and not a cloned UID) is NOT implemented in either backend. UID-only
// reading is sufficient for a UID-keyed pilot but is CLONEABLE. See
// authenticateDesfire() -- a clearly-marked TODO that needs real hardware +
// the card's diversified AES key set to validate.
// =============================================================================
#pragma once

#include <Arduino.h>

struct CardTap {
    String uid;        // uppercase hex, no separators, e.g. "04A2B3C4D5E6F0"
    bool   authenticated = false;  // true only if DESFire AES auth succeeded
};

class CardReader {
public:
    virtual ~CardReader() {}

    // Initialize the reader hardware. Returns false if the chip is not found.
    virtual bool begin() = 0;

    // Poll once for a present card. Returns true and fills `tap` if a NEW card
    // is detected this cycle; false if no card. Non-blocking-ish (short timeout).
    virtual bool poll(CardTap& tap) = 0;

    // Human-readable backend name for logs/UI.
    virtual const char* name() const = 0;

    // -------------------------------------------------------------------------
    // TODO(desfire): Perform DESFire mutual 3-pass AES authentication against
    // the application master key (or a UID-diversified key). On success the card
    // is proven genuine and a secure-messaging session key is established, which
    // is what lets you trust the UID and (optionally) store value in a protected
    // file on-card. Requires:
    //   - real PN532 (or equivalent) hardware
    //   - the card's AES key set / key diversification scheme (KDF + master key)
    //   - DESFire APDU exchange (0x0A AuthenticateAES, RndA/RndB rotation)
    // Until implemented this returns false and callers must treat the UID as
    // UNVERIFIED (cloneable). Do not ship value-on-card without this.
    // -------------------------------------------------------------------------
    virtual bool authenticateDesfire(CardTap& tap) {
        (void)tap;
        return false;  // not implemented -- UID is unverified
    }
};

// Factory: returns the backend selected at build time (USE_PN532_HW).
CardReader& cardReader();
