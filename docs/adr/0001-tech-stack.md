# ADR 0001 — Technology Stack

- **Status:** Accepted
- **Date:** 2026-07-04
- **Context owner:** Architecture review

## Context

The product is a cloud-native **cashless card + management platform for arcades / family-entertainment centers (FECs)** in MENA. A customer taps an RFID/NFC card at a reader to pay-per-play; staff top up cards; owners see live revenue; later stages add online top-up, a customer app, and cross-venue value. Constraints that drive the choices:

- **Solo, software-focused founder**, ~US$10–50k budget; optimizing for a **fast paying pilot** *and* a **fundraise-ready** codebase.
- First-order concerns: **money correctness**, **offline resilience** (flaky venue internet), **multi-tenant isolation**, **Arabic/RTL**, and a **secure card reader**.
- Beachhead Egypt (Cairo/Giza) → GCC. Hardware is **bought/white-labeled**, not manufactured.

## Decision

Adopt a deliberately "boring and right" stack.

| Layer | Choice |
|---|---|
| **Backend** | Python 3.11 · FastAPI · Uvicorn · SQLAlchemy 2.0 · Alembic · Pydantic v2 |
| **Auth/Security** | JWT (python-jose) + refresh, bcrypt (passlib), TOTP MFA (pyotp), slowapi rate-limiting, Ed25519 (cryptography) for offline reader envelopes |
| **Database** | PostgreSQL 15 (UUID PKs, DECIMAL money, JSONB, ENUMs); double-entry ledger; Row-Level Security for tenancy |
| **Frontend** | Vue 3 + Vite + TypeScript (strict) · PrimeVue v4 · Pinia · Vue Router · vue-i18n (Arabic/RTL) · axios |
| **Reader firmware** | ESP32 + PN532 (MIFARE DESFire EV2/EV3) — server-authoritative balances; Arduino for bring-up, **ESP-IDF for production** |
| **Infra/DevOps** | Docker + docker-compose; GitHub Actions CI; target hosting Fly.io/Render + managed Postgres (PITR); managed MQTT (EMQX/HiveMQ) for the device bus |
| **Payments (staged, behind a licensed PSP)** | Paymob / Fawry / Meeza (Egypt); Geidea / HyperPay / Tap (GCC) via hosted checkout (PCI SAQ-A) |

## Alternatives considered

- **Backend: Go / .NET / Node+TS.** Better raw throughput / compile-time guarantees, but not the bottleneck at pilot scale; Python wins on solo velocity and MENA hiring pool.
- **Database: MySQL / NoSQL.** Rejected NoSQL outright — money is relational and needs ACID + a ledger. Postgres additionally gives RLS + JSONB.
- **Frontend: React/Next.** Larger global hiring pool, but Vue is very hireable in the region and the Arabic/RTL work is already done — no reason to reset it.
- **Reader: STM32 / dedicated reader ICs; building a custom PCB first.** Rejected for a software founder — ESP32 + off-the-shelf/ODM is cheaper and faster; custom PCB only after ~500 units of demand.
- **Microservices / Kubernetes.** Rejected — a modular monolith on managed PaaS is correct for a solo team; splitting the ledger would break consistency.

## The key insight

**The stack is not where the risk lives.** Success is decided by three things the stack merely *enables*: (1) money correctness (double-entry ledger, idempotency), (2) offline resilience (signed offline tokens + reconciliation), and (3) reader security (DESFire + server-authoritative balances). Engineering effort should concentrate there, not on framework choice.

## Consequences

- **Positive:** high solo velocity, strong hiring pool, ACID money data, low ops burden, a fundraise-legible architecture, and a clean path to scale (read replicas → regional stacks → activate payments/customer modules) without a rewrite.
- **Trade-offs:** Python has lower per-instance throughput than Go/.NET (irrelevant at pilot scale); PrimeVue v4 RTL has known overlay-positioning quirks (patched via `rtl-overrides.scss` + pinned version).
- **Anti-patterns explicitly avoided:** money-on-card, custom crypto, NoSQL for money, microservices, and building hardware before validating demand.

## Open decisions

- **Firmware framework:** Arduino (prototype) → **ESP-IDF** (production) for robust mTLS / OTA / NVS. Make this switch deliberately before shipping readers.

## References

Companion artifacts: Master Architecture & Business Blueprint; Functional Verification Report; the prioritized post-blueprint backlog.
