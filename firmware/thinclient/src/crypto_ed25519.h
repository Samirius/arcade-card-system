// =============================================================================
// crypto_ed25519.h  --  Ed25519 detached-signature verification
// =============================================================================
// Used to verify the offline-envelope signature against the PINNED public key
// in config.h before the device is allowed to authorize any offline play.
//
// IMPLEMENTATION: This uses the libsodium that ships *inside* the ESP32 Arduino
// framework (framework-arduinoespressif32), via crypto_sign_verify_detached.
// The framework already adds libsodium's include path and links -llibsodium, so
// no extra lib_dep is required. This is a REAL verification, not a stub.
//
// If, on some other framework revision, libsodium is unavailable, define
// TC_NO_LIBSODIUM at build time to fall back to a clearly-marked stub that
// FAILS CLOSED (returns false) -- it never fakes a "true" result.
// =============================================================================
#pragma once

#include <Arduino.h>
#include <stddef.h>
#include <stdint.h>

namespace tccrypto {

// Verify a 64-byte Ed25519 signature over `msg` using a 32-byte public key.
// Returns true iff the signature is valid. Constant-time inside libsodium.
bool ed25519Verify(const uint8_t* msg, size_t msgLen,
                   const uint8_t* sig64,
                   const uint8_t* pubkey32);

// True if this build has a real crypto backend (libsodium) compiled in.
// false means ed25519Verify is the fail-closed stub.
bool ed25519Available();

}  // namespace tccrypto
