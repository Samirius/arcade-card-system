// =============================================================================
// crypto_ed25519.cpp
// =============================================================================
#include "crypto_ed25519.h"

#if !defined(TC_NO_LIBSODIUM)
// libsodium ships with framework-arduinoespressif32. The framework build script
// adds .../include/libsodium/... to the include path and links -llibsodium.
#include <sodium/crypto_sign.h>

namespace tccrypto {

bool ed25519Available() { return true; }

bool ed25519Verify(const uint8_t* msg, size_t msgLen,
                   const uint8_t* sig64,
                   const uint8_t* pubkey32) {
    if (!msg || !sig64 || !pubkey32) return false;
    // crypto_sign_verify_detached returns 0 on success (valid signature).
    return crypto_sign_verify_detached(sig64, msg, (unsigned long long)msgLen,
                                       pubkey32) == 0;
}

}  // namespace tccrypto

#else  // ------------------------------------------------------------------ stub

// -----------------------------------------------------------------------------
// FAIL-CLOSED STUB. Compiled only when TC_NO_LIBSODIUM is defined (i.e. a
// framework build without bundled libsodium). This does NOT verify anything and
// intentionally returns false so the device refuses to authorize offline until a
// real Ed25519 backend is wired in.
//
// TODO(crypto): If you must build without libsodium, integrate a vetted Ed25519
// implementation here (e.g. the `rweather/Crypto` Arduino lib's Ed25519 class,
// or ESP-IDF's mbedTLS PK API in the recommended ESP-IDF port -- see README).
// Do NOT change this to `return true`.
// -----------------------------------------------------------------------------
namespace tccrypto {

bool ed25519Available() { return false; }

bool ed25519Verify(const uint8_t*, size_t, const uint8_t*, const uint8_t*) {
    return false;  // fail closed -- signature NOT verified
}

}  // namespace tccrypto

#endif
