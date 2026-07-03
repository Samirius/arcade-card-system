# Arcade Card System — Thin Client Reader Firmware

A **server-authoritative thin client** reader for ESP32. Unlike the legacy
offline kiosk sketch (`firmware/card_kiosk_mvp.ino`, left untouched), this
firmware treats the **cloud as the source of truth**:

- **Online:** read a card → `POST /api/v1/charge` → the server debits and returns
  the authoritative balance. No balance is trusted locally.
- **Offline:** if the network is down, authorize **only within a server-signed
  Ed25519 "offline envelope"** (per-transaction + cumulative caps), append a
  tamper-evident record to flash, and **reconcile** the batch when connectivity
  returns.

> **Status: bench scaffold, not a finished product.** The online charge path and
> the offline store/reconcile logic are implemented and **compile-verified** (see
> below). The contactless front-end defaults to a **stub UID source**, and
> **DESFire mutual AES authentication is a documented TODO** that needs real
> hardware to validate. See *Implemented vs. stubbed*.

---

## Build & verify

This is deliberately an **Arduino-framework** PlatformIO project so it compiles
in CI without the full ESP-IDF toolchain.

```bash
# from the repo root
pip install platformio            # if not already installed
PLATFORMIO_CORE_DIR=/agent/workspace/.pio \
  pio run -d firmware/thinclient
```

Last verified result on this environment:

```
RAM:   14.4% (47,288 / 327,680 bytes)
Flash: 75.5% (988,945 / 1,310,720 bytes)
[SUCCESS]
```

Both build variants compile and link:

| Env / flag                 | Card front-end            | Result    |
|----------------------------|---------------------------|-----------|
| default (`USE_PN532_HW=0`)  | stub UID source           | SUCCESS   |
| `USE_PN532_HW=1`            | real `Adafruit_PN532` I2C | SUCCESS   |

To build against real PN532 hardware:

```bash
PLATFORMIO_CORE_DIR=/agent/workspace/.pio \
PLATFORMIO_BUILD_FLAGS="-UUSE_PN532_HW -DUSE_PN532_HW=1" \
  pio run -d firmware/thinclient
```

(or uncomment the `[env:esp32dev_pn532]` block in `platformio.ini`).

---

## Backend contract implemented

All requests carry `Authorization: Bearer <device_token>` and, in production,
validate the server against a **pinned root CA**.

| Method & path | Request | Response |
|---|---|---|
| `POST /api/v1/charge` | `{ card_uid, price_cents, sku, client_txn_id (uuid), nonce, ts }` | `{ result: "approved"\|"declined", balance_after_cents, server_txn_id }` |
| `GET /api/v1/devices/{id}/offline-envelope` | — | `{ offline_cap_cents, per_txn_cap_cents, valid_until, key_id, signature }` |
| `POST /api/v1/reconcile` | `{ batch:[{card_uid, price_cents, client_txn_id, seq, ts}], key_id }` | 2xx = accepted |

**Idempotency:** `client_txn_id` is a UUIDv4 generated **once** per logical
transaction and reused across HTTP retries *and* across the offline→reconcile
handoff, so a charge is never double-applied.

> **Note on the current repo backend.** The FastAPI service in `backend/` today
> exposes a *related but differently-shaped* offline API
> (`/offline/token/issue`, JWT-signed per-card tokens, `/transactions/`, etc.).
> This firmware targets the `/api/v1/{charge,offline-envelope,reconcile}`
> contract given as the spec. Aligning the two is a backend task; per the
> assignment, `backend/` was **not modified**. The canonical request/response
> shapes live in `src/net_client.*` and the envelope format in
> `src/offline_store.*` so the backend can mirror them.

---

## Auth model

- **Pilot (implemented):** static per-device bearer token, provisioned into NVS
  (`tc-cfg/dev_token`). The compile-time `DEFAULT_DEVICE_TOKEN` is a placeholder
  and must be replaced per device.
- **Production upgrade (documented):** **mTLS / X.509 client certificates.**
  `WiFiClientSecure` already supports `setCertificate()` / `setPrivateKey()`;
  the hook is marked in `net_client.cpp::applyTls()`. Per-device certs remove the
  shared-secret risk of bearer tokens and let the server pin device identity at
  the TLS layer.

---

## Envelope signing (must match on both sides)

The device verifies the envelope's `signature` (Ed25519, 64 bytes; accepts
base64 or hex) against the **pinned public key** in `config.h`
(`TC_ENVELOPE_PUBKEY`) over this exact canonical string:

```
v1|<device_id>|<offline_cap_cents>|<per_txn_cap_cents>|<valid_until>|<key_id>
```

- `valid_until` is unix seconds, no trailing newline, UTF-8.
- The envelope's `key_id` must equal the pinned `TC_ENVELOPE_KEY_ID` (rejects key
  confusion).
- The backend signer must produce the signature over **byte-identical** input.

Offline authorization is permitted **iff**: a valid, unexpired envelope exists,
`price_cents ≤ per_txn_cap_cents`, and `pending_spent + price_cents ≤
offline_cap_cents`.

**Ed25519 verification is real, not stubbed** — it uses the `libsodium`
(`crypto_sign_verify_detached`) that ships inside the ESP32 Arduino framework;
the framework already adds its include path and links `-llibsodium`. (Verified:
the symbol is present in the linked `firmware.elf`.) If a future framework lacks
libsodium, define `TC_NO_LIBSODIUM` — verification then falls back to a
**fail-closed stub** in `crypto_ed25519.cpp` that returns `false` and never fakes
success.

**Offline log integrity:** each stored record carries an HMAC-SHA256 tag
(mbedTLS, device-local key auto-generated in NVS on first boot) so a queued
transaction cannot be silently edited on-device before it reconciles.

---

## Implemented vs. stubbed

| Area | State |
|---|---|
| Online charge flow (build JSON, POST, parse `result`/balance, retry idempotently) | **Implemented** |
| WiFi connect + SNTP time sync + periodic reconnect | **Implemented** |
| Offline authorization within signed caps | **Implemented** |
| Ed25519 envelope signature verification | **Implemented (real, libsodium)** |
| Append-only NVS transaction log + HMAC integrity | **Implemented** |
| Reconcile batch build + upload + prune-on-ack | **Implemented** |
| Monotonic `seq` (NVS) + `client_txn_id` (UUIDv4) + `nonce` (HW RNG) | **Implemented** |
| LED/buzzer UI states (serial stands in for a display) | **Implemented** |
| PN532 UID read (I2C) | **Implemented** (behind `USE_PN532_HW=1`) |
| **DESFire EV2/EV3 mutual AES auth** | **STUBBED — TODO** (`card_reader.h::authenticateDesfire`) |
| Card front-end default | **STUB UID** (`04DEADBEEF0102`) for CI/bench |
| TLS server-cert pinning | Hook present; ships with placeholder CA → bench uses `setInsecure()` |
| Provisioning UI (serial/BLE to write NVS config) | Not implemented (config via NVS keys / compile-time defaults) |

Why the stubs are honest: with the shipped **all-zero** `TC_ENVELOPE_PUBKEY` and
**placeholder** CA, the device **fails closed** — real signatures won't verify
and offline play stays disabled until a real key/CA is pinned. The DESFire stub
returns `false`, so the UID is always flagged **unverified** (cloneable); do not
ship value-on-card behaviour without implementing it.

---

## Wiring (ESP32 DevKitC)

**PN532 (NFC front-end, I2C mode)** — set the PN532 DIP switches to I2C:

| PN532 | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |
| IRQ | GPIO16 |
| RSTO | GPIO17 |

**Status LED (common-cathode RGB, active-high; use ~330 Ω series resistors)**

| LED | ESP32 |
|---|---|
| R | GPIO25 |
| G | GPIO26 |
| B | GPIO27 |
| cathode | GND |

**Buzzer (piezo, driven by LEDC PWM)**

| Buzzer | ESP32 |
|---|---|
| + | GPIO32 |
| − | GND |

**Display:** the scaffold prints status to the serial console (115200 baud). A
TFT/OLED drops in behind `ui::showLines()` without touching the state machine.
If you add an SPI TFT, keep it off GPIO21/22 (reserved for PN532 I2C here).

LED colour key: blue=boot/charging, green(blink)=idle, green=approved-online,
yellow=approved-offline, magenta=syncing, red=declined/no-caps/error.

---

## Configuration

Runtime config is read from NVS namespace `tc-cfg`, falling back to the
compile-time defaults in `src/config.h`. Keys:

| NVS key | Meaning |
|---|---|
| `wifi_ssid`, `wifi_pass` | WiFi credentials |
| `base_url` | cloud base URL (**must be `https://`**) |
| `device_id` | logical device id (used in envelope + reconcile) |
| `dev_token` | bearer token |
| `price_cents` | fixed play price |
| `play_sku` | product SKU |

For production also replace in `config.h`: `TC_ENVELOPE_PUBKEY` (+
`TC_ENVELOPE_KEY_ID`) and `TC_SERVER_ROOT_CA_PEM`, and set
`-DTHINCLIENT_ALLOW_INSECURE_TLS=0` so the money path fails closed without a
pinned CA.

---

## Source layout

```
firmware/thinclient/
├── platformio.ini          # esp32dev, Arduino framework, lib_deps, build guards
├── README.md
└── src/
    ├── main.cpp            # boot + loop; owns g_deviceId; SNTP; reconnect/reconcile
    ├── config.h/.cpp       # NVS-backed config + pinned pubkey/CA
    ├── ids.h/.cpp          # monotonic seq + UUIDv4 client_txn_id + nonce
    ├── crypto_ed25519.h/.cpp  # REAL Ed25519 verify (libsodium) / fail-closed stub
    ├── card_reader.h/.cpp  # CardReader interface; PN532 backend + stub; DESFire TODO
    ├── offline_store.h/.cpp# envelope verify+cache; signed NVS log; reconcile batch
    ├── net_client.h/.cpp   # WiFiClientSecure+HTTPClient; charge/envelope/reconcile
    ├── charge_fsm.h/.cpp    # online-first, offline-fallback charge state machine
    └── ui.h/.cpp           # LED/buzzer/display states
```

---

## Recommended production migration: ESP-IDF

This project uses the **Arduino framework** so it can be **compile-verified in CI
without the full ESP-IDF toolchain**. For production, migrating to **ESP-IDF** is
recommended because:

- **Secure boot v2 + flash encryption** — protect firmware authenticity and the
  device token / keys at rest (a money terminal requirement).
- **First-class NVS encryption** and a robust OTA/rollback story.
- **mTLS via `esp-tls` / mbedTLS PK** with the private key in an eFuse-protected
  secure element (ATECC608 / built-in DS peripheral) instead of flash.
- **Task/watchdog control, brownout handling, power management** — deterministic
  behaviour for an always-on unattended reader.
- **A supported DESFire/PN532 stack** and direct APDU control for the mutual-AES
  auth that this scaffold stubs.

The code is already split into hardware-agnostic modules (`CardReader` interface,
`tccrypto` verify wrapper, `offline::` store, `net::` transport) to make that port
mechanical: the interfaces stay, only the backends change.

---

## What still needs a real board to validate

- **DESFire mutual AES authentication** — needs PN532 hardware + the card key set
  / diversification scheme; UID-only is cloneable.
- **Real PN532 UID reads and debounce timing** — the I2C path compiles but was
  not exercised against silicon.
- **End-to-end money path against a live backend** — TLS handshake with the
  *pinned* CA, real `/charge` approve/decline, and idempotent retry behaviour.
- **Ed25519 envelope round-trip** — sign an envelope with the backend private key
  and confirm the device accepts it (and rejects tampered/expired/wrong-`key_id`
  ones). Verification logic is linked and unit-shaped but untested against a real
  server signature.
- **NVS wear / capacity** under a large offline backlog, and power-loss safety of
  the append/prune sequence.
- **SNTP availability** and envelope-expiry behaviour when the RTC is cold.
- **Buzzer/LED GPIO conflicts** with whatever display/enclosure is chosen.
```
