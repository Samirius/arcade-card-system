# Frontend Changes — Token Storage, Field Normalization Removal, Cashier PWA Scaffold

**Status: DRAFT / NOT BUILD-VERIFIED.**

> **`npm install` was BLOCKED in the authoring sandbox** (`npm ping` returned
> `403 Forbidden` from `registry.npmjs.org` — a registry policy restriction,
> not a transient failure). As a direct consequence, **none of the code below
> has been installed, type-checked, built, linted, or run** in any way. No
> claim in this document should be read as "this works" — only as "this is
> what was written, and this is the reasoning behind it." Every file was
> written by hand, re-read carefully, and cross-checked against the actual
> backend source (read-only) for field-name accuracy, but hand-verification
> is not a substitute for a real `tsc`/`vite build`/browser run. Treat this
> entire patch as an unverified draft PR that still needs its first real CI
> run.

Scope of this patch: **`frontend/` only.** No files under `backend/` or
`firmware/` were read for editing purposes (only read for reference, to get
exact field names right) or modified. No `git` commands were used.

---

## 1. Token storage fix — in-memory access token + cookie-based refresh

### What changed

- **New file:** `frontend/src/lib/tokenStore.ts` — a plain module-level
  singleton (`getAccessToken()` / `setAccessToken()` / `clearAccessToken()` /
  `hasAccessToken()`). This is now the *only* place the access token value
  lives on the client.
- **`frontend/src/config/api.ts`** (rewritten):
  - Removed all `localStorage.getItem`/`setItem`/`removeItem` calls for the
    access token.
  - Added `withCredentials: true` to the shared axios instance, required so
    the browser will send/receive the httpOnly refresh cookie described
    below.
  - Request interceptor now reads the token from `tokenStore.getAccessToken()`
    on every request instead of a static default header.
  - Response interceptor implements **single-flight 401 refresh**: the first
    401 triggers exactly one `POST /api/v1/auth/refresh` call; any other
    requests that 401 concurrently await that same in-flight promise instead
    of each starting their own refresh (see `performRefresh()` /
    `refreshPromise` in `api.ts`). On refresh success, the original request(s)
    are retried once with the new token. On refresh failure, the in-memory
    token is cleared (`clearAccessToken()`), which is what pushes the app
    into a logged-out state on next navigation/guard check.
  - Requests to `/auth/login` and `/auth/refresh` itself are explicitly
    excluded from the retry-on-401 logic (to avoid infinite loops / masking
    real login failures).
- **`frontend/src/stores/auth.ts`** (rewritten):
  - `setToken()` / `clearToken()` now delegate to `tokenStore` instead of
    touching `localStorage` or `api.defaults.headers.common['Authorization']`.
  - `init()` no longer gates session restore on a `localStorage` flag (there
    is nothing left to gate on). It now unconditionally attempts
    `POST /api/v1/auth/refresh` on app start; success silently restores the
    session, failure leaves the user logged out. This is the intended
    "silent session restore from httpOnly cookie" pattern.
  - No changes were needed in `frontend/src/router/index.ts` — its navigation
    guard already calls `auth.init()` conditionally in a way that's
    compatible with this change (confirmed by reading it; not modified).

### Why

Storing a long-lived bearer access token in `localStorage` means any XSS
payload that ever executes on the page can read it and exfiltrate it for
replay indefinitely. An in-memory-only token is still usable by an XSS
payload for the lifetime of that page load, but it can no longer be silently
read off disk and replayed later, and it disappears on tab close/reload.

### ⚠️ Required backend coordination (NOT done by this patch)

This is a **contract change that only works with a matching backend change.**
Read `backend/app/api/auth.py` (read-only, for reference) confirms:

- `/auth/login`, `/auth/login/mfa`, and `/auth/refresh` currently return
  `refresh_token` in the **JSON response body**.
- `/auth/refresh` already has fallback logic to read a refresh token from
  `request.cookies.get("refresh_token")`, but **nothing anywhere calls
  `response.set_cookie(...)`** — so today, no httpOnly cookie is ever
  actually set. That fallback path is currently dead code.

**Until the backend ships the following, `init()` will always fail and every
full page reload will force a fresh login** — this is expected during the
migration window, not a bug in this patch:

1. On `/auth/login`, `/auth/login/mfa`, and `/auth/refresh` success, set an
   `httpOnly` + `Secure` + `SameSite=strict|lax` cookie (e.g. `refresh_token`)
   instead of (or alongside, temporarily) returning it in the body.
2. Stop returning `refresh_token` in the JSON body once the frontend
   migration is confirmed deployed — leaving it in the body defeats the
   purpose (it becomes reachable by JS/XSS again).
3. Promote the existing cookie-read fallback in `/auth/refresh` to the
   primary path, keeping server-side rotation/invalidation as-is.
4. Confirm CORS is configured with `allow_credentials=True` and an explicit,
   non-wildcard `allow_origins` list — cookies are not sent cross-origin with
   `Access-Control-Allow-Origin: *`.

Full detail and rationale is in the top-of-file comment in
`frontend/src/lib/tokenStore.ts` — read that before touching this area.

---

## 2. Kill field normalization — raw backend field names + typed client tooling

### What changed

- **Removed** the `normalizeCardFields()` response-interceptor shim from
  `frontend/src/config/api.ts` entirely. Responses now pass through
  untouched; components receive exactly what FastAPI/Pydantic serializes.
- **Added tooling** to generate a typed client from the backend's live
  OpenAPI schema instead of hand-maintaining a rename layer:
  - `devDependencies`: `openapi-typescript`, `openapi-fetch` (added in
    `frontend/package.json`).
  - New npm script: `"gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts"`.
  - **New placeholder file:** `frontend/src/lib/api-types.ts` — hand-written,
    clearly marked as a placeholder (NOT generated), with instructions for
    the founder to run `npm run gen:api` against a real running backend and
    overwrite it. It exports two minimal interfaces
    (`PlaceholderCardResponse`, `PlaceholderTransactionResponse`) purely so
    nothing hard-fails on import before generation has actually happened.
- **Refactored 11 Vue components** to read raw backend field names instead of
  the old normalized ones. Every one of these files has an inline comment
  pointing back to this document. Full list:

  | File | Old (normalized) fields used | New (raw backend) fields |
  |---|---|---|
  | `src/views/admin/CardDetailView.vue` | `card.uid`, `card.type`, `card.customer_name`, `data.type` | `card.card_uid`, `card.card_type`, `card.owner`, `data.transaction_type` |
  | `src/views/admin/CardsView.vue` | `c.uid`, `c.customer_name`, `c.type`, `e.data.uid` | `c.card_uid`, `c.owner`, `c.card_type`, `e.data.card_uid` |
  | `src/views/admin/DashboardView.vue` | `data.type` (recent transactions table) | `data.transaction_type` |
  | `src/views/admin/TransactionDetailView.vue` | `transaction.type` | `transaction.transaction_type` |
  | `src/views/admin/TransactionsView.vue` | `type` (Column field, severity map, sign) | `transaction_type` |
  | `src/views/cashier/CashierBalance.vue` | `card.uid`, `card.customer_name`, `card.type` | `card.card_uid`, `card.owner`, `card.card_type` |
  | `src/views/cashier/CashierHistory.vue` | `txn.type` | `txn.transaction_type` |
  | `src/views/cashier/CashierHome.vue` | `txn.type` | `txn.transaction_type` |
  | `src/views/cashier/CashierRegister.vue` | request body `{ uid, customer_name }` | request body `{ card_uid, owner }` — **see bug note below** |
  | `src/views/portal/PortalBalance.vue` | `card.uid`, `card.type` | `card.card_uid`, `card.card_type` |
  | `src/views/portal/PortalHistory.vue` | `txn.type` | `txn.transaction_type` |

  A final verification pass (`grep` across `src/views` for `\.type\b`,
  `\.uid\b`, `customer_name`) was run after finishing the edits above to
  catch stragglers. It caught `PortalHistory.vue`, which had been missed on
  the first pass (fixed). The only remaining matches after the second pass
  are i18n translation keys (e.g. `t('card.uid')`, `t('transaction.type')` —
  these are label lookups, not data bindings, so they're unrelated), local
  route-param variables (`route.params.uid`), and this document's own
  explanatory comments.

- **`src/stores/auth.ts`**: `normalizeUser()` was **kept as-is** and is
  explicitly called out in a comment as *not* the same kind of thing as the
  removed `normalizeCardFields` — the backend genuinely returns separate
  `first_name`/`last_name` fields with no combined field to rename from, so
  deriving `full_name` client-side is a legitimate UI convenience, not a
  contract-hiding rename.

### Why

The old `normalizeCardFields` silently renamed backend fields
(`card_uid → uid`, `owner → customer_name`, `card_type`/`transaction_type` →
`type`) on every response. This is a silent contract-drift trap: if the
backend ever added, removed, or renamed a field, nothing would fail loudly —
a component would just silently receive `undefined` where it expected a
value, discoverable only by a user noticing a blank UI in production.
Generating types directly from the backend's real OpenAPI schema turns that
category of bug into a TypeScript compile error at build time instead.

### Bug found (pre-existing, not introduced by this patch): `CashierRegister.vue`

While doing the field-name audit, I found that `CashierRegister.vue`'s
card-registration POST body used `{ uid, customer_name }` — field names that
**never matched** the backend's real `CardCreate` schema
(`backend/app/schemas/business.py`, which is the schema actually imported by
`backend/app/api/cards.py` — **not** `backend/app/schemas/card.py`, which
defines a similarly-named but unused schema). The real schema requires
`card_uid` (required) and `owner` (required, `min_length=1`). Since the old
normalization layer only ever ran on *responses*, never on outgoing request
*bodies*, this means card registration from the cashier UI was very likely
already broken (422 from FastAPI/Pydantic) before this patch, independent of
anything done here. **Fixed** the field names to `card_uid` / `owner` at the
request boundary (local form field names `form.uid` / `form.customer_name`
were left as-is since they're just UI-facing variable names).

**⚠️ Unresolved gap — flagged, not guessed:** `owner` is a required,
non-empty field server-side, but the "customer name" input in this form has
no required-field validation and can be submitted blank, which will still
send `owner: undefined` and likely trigger a 422. This needs a product
decision during the verified build: either (a) make customer name required
in the UI, or (b) ask the backend to make `owner` optional / default it.
**Deliberately left unresolved** — guessing the wrong direction here would be
worse than leaving it visible for the founder to decide.

### Package version caveat

`package.json` now lists `openapi-typescript@^7.5.2`, `openapi-fetch@^0.13.4`
(devDependencies) and `idb@^8.0.1` (dependencies — see PWA section below for
why `idb` isn't a devDependency). **These version numbers were not checked
against the live npm registry** (couldn't be — see the blocker at the top of
this document) and were chosen from general familiarity with the packages'
release lines at authoring time. Run `npm install` and let npm resolve
against its lockfile / the real registry; if any of these ranges are stale or
wrong, `npm install` will surface it immediately and the fix is just editing
the version range.

---

## 3. Cashier PWA scaffold — installable shell + offline command queue

### What changed

- **`vite.config.ts`**: added the `vite-plugin-pwa` plugin
  (`devDependencies`) with `registerType: 'autoUpdate'`, a manifest (name,
  short_name, `start_url: '/cashier'`, colors), and
  `workbox.navigateFallbackDenylist: [/^\/api\//]` so navigation-fallback
  routing can never accidentally serve cached `index.html` in place of a
  failed API response. `runtimeCaching` is left empty on purpose (see gap
  note below). Manifest `icons` array is present but **commented out** — no
  actual icon PNGs exist in `public/` yet, so real files need to be added
  under e.g. `public/pwa/` before the commented lines are uncommented;
  otherwise the manifest would point at 404s.
- **New file:** `frontend/src/lib/offlineQueue.ts` — a generic,
  IndexedDB-backed (via the `idb` library) queue of pending mutating
  commands:
  - `enqueue(kind, endpoint, body)` — persists a command immediately with a
    client-generated UUID v4 idempotency key (via `crypto.randomUUID()`,
    with a manual fallback for very old browsers).
  - `drain(postFn)` — replays the queue in order against an **injected**
    poster function (so this module has no compile-time dependency on axios
    and stays trivially unit-testable). A command is removed from the queue
    **only after the server confirms success** — the server response is
    always the source of truth, never an optimistic local assumption.
    Stops at the first failure in a drain pass rather than hammering the API
    with the rest of the queue.
  - `initConnectivityWatcher(postFn)` — registers `window` `online`/`offline`
    listeners exactly once and auto-drains on reconnect.
  - `onConnectivityChange()`, `isOnline()`, `listPending()`, `pendingCount()`
    as supporting utilities.
  - A worked example usage block at the bottom of the file shows how this
    would wire into e.g. `CashierBalance.vue`'s add-credit handler.
- **`idb` was added to `dependencies`, not `devDependencies`**, despite the
  original task description grouping it with other dev tooling. This is a
  deliberate deviation: `offlineQueue.ts` imports `idb` at **runtime** (it's
  what actually talks to IndexedDB in the shipped cashier bundle), so it
  needs to be a real dependency or the production build would be missing it
  from `node_modules` in a strict/clean-install deploy pipeline. Flagging
  this explicitly rather than silently doing something different than
  instructed.

### What this scaffold deliberately does NOT do

Per the task brief, this is a **scaffold**, not a full offline POS rebuild:

- `offlineQueue.ts` is **not wired into any component**. `CashierBalance.vue`
  (the natural integration point for add-credit/charge) still calls
  `api.post(...)` directly and does not fall back to `enqueue()` on network
  failure. The example usage comment at the bottom of `offlineQueue.ts` shows
  exactly how that wiring would look; actually wiring it up (plus the UI for
  "N actions pending sync", retry buttons, etc.) is left for a follow-up.
- Runtime caching of GET API responses (`workbox.runtimeCaching`) is left
  empty. Caching card balances is a financial-data caching decision (stale
  balance shown to a cashier is a real risk) that needs explicit product
  sign-off, not a default I should have picked unilaterally.

### ⚠️ Hard blocker before enabling `drain()` on any real money flow

Grepped the backend (`grep -rn "idempot"` across `backend/`) and confirmed
**there is no idempotency-key support anywhere server-side** — no unique
constraint or dedupe lookup on any header or field for
`backend/app/api/cards.py`'s `/cards/{card_uid}/add-credit` or `/charge`
endpoints. This means: if a `drain()` POST actually succeeds on the server
but the response is lost in transit (e.g. the connection drops right after
the server commits), replaying that same queued command **will double-charge
or double-credit the card**. The idempotency key is sent defensively in the
`Idempotency-Key` header today so that wiring it up server-side later is a
one-sided backend change, but it currently provides **zero protection**.

**Do not enable `drain()` on any real cashier flow in production until the
backend accepts and enforces an idempotency key on both of those endpoints.**
This is called out prominently at the top of `offlineQueue.ts` as well — this
is real cash-drawer money, treat it as a hard blocker, not a nice-to-have.

---

## Files created

- `frontend/src/lib/tokenStore.ts`
- `frontend/src/lib/api-types.ts` (placeholder — see item 2)
- `frontend/src/lib/offlineQueue.ts`
- `frontend/FRONTEND_CHANGES.md` (this file)

## Files modified

- `frontend/src/config/api.ts` (rewritten)
- `frontend/src/stores/auth.ts` (rewritten)
- `frontend/package.json` (scripts + dependencies/devDependencies)
- `frontend/vite.config.ts` (added VitePWA plugin)
- `frontend/src/views/admin/CardDetailView.vue`
- `frontend/src/views/admin/CardsView.vue`
- `frontend/src/views/admin/DashboardView.vue`
- `frontend/src/views/admin/TransactionDetailView.vue`
- `frontend/src/views/admin/TransactionsView.vue`
- `frontend/src/views/cashier/CashierBalance.vue`
- `frontend/src/views/cashier/CashierHistory.vue`
- `frontend/src/views/cashier/CashierHome.vue`
- `frontend/src/views/cashier/CashierRegister.vue`
- `frontend/src/views/portal/PortalBalance.vue`
- `frontend/src/views/portal/PortalHistory.vue`

Nothing under `backend/` or `firmware/` was modified. `git` was not used at
any point during this patch.

---

## BUILD-VERIFICATION CHECKLIST

**None of the following has been run in the authoring environment.** This is
the exact sequence the founder (or CI) needs to run on a machine with real
npm registry access and a runnable backend, before trusting any of this code.

### 1. Install

```bash
cd frontend
npm install
```

Expect this to surface any wrong/stale version ranges in the four new
packages (`idb`, `openapi-fetch`, `openapi-typescript`, `vite-plugin-pwa`) —
fix ranges in `package.json` if `npm install` complains.

### 2. Generate the typed API client against a running backend

```bash
# In one terminal, from backend/ (however it's normally run):
uvicorn app.main:app --reload   # or the project's actual run command
# Confirm http://localhost:8000/openapi.json is reachable in a browser first.

# In frontend/:
npm run gen:api
```

This overwrites `frontend/src/lib/api-types.ts` with real generated types.
Confirm the file no longer contains the `Placeholder*` interfaces / the
"NOT been generated yet" header comment afterward — if it still does, the
command silently failed and needs investigating (wrong backend URL, backend
not running, etc).

### 3. Type-check + build

```bash
npm run build
```

(`build` runs `vue-tsc -b && vite build` per `package.json` — this is the
first real TypeScript check any of this code will have ever gotten.) Expect
to have to fix real type errors here — nothing in this patch has been
through `tsc` yet.

### 4. Dev server smoke test

```bash
npm run dev
```

Then, against a real running backend:

1. **Login + MFA flow**: log in with a user that has MFA enabled; confirm
   the MFA prompt appears and a valid code completes login successfully.
2. **Token no longer in localStorage**: open browser DevTools →
   Application/Storage → Local Storage for the app's origin. Confirm there is
   **no** `sindbad-access-token` (or similarly named) key present, before and
   after login. (It is normal/expected for the session to be lost on a full
   page reload **unless** the backend has also shipped the httpOnly refresh
   cookie described in item 1 above — if it hasn't yet, a reload requiring
   re-login is the correct, expected behavior for this migration state, not
   a bug.)
3. **A top-up round-trips**: as a cashier user, search for or register a
   card, perform an "add credit" (top-up), and confirm the new balance is
   reflected in the UI immediately after the request completes — and that no
   console errors reference undefined fields (would indicate a missed
   field-normalization call site).
4. **Offline queue drains on reconnect**: this scaffold is not wired into any
   UI flow yet (see item 3 above), so there is no built-in smoke test for it
   through the UI. To manually verify the module itself works: import
   `enqueue`/`drain`/`initConnectivityWatcher` from `src/lib/offlineQueue.ts`
   in a scratch component or the browser console, call `enqueue('test',
   '/api/v1/some-safe-get-or-noop-endpoint', {})`, toggle DevTools' Network
   "Offline" throttling on/off, and confirm `drain()` — or the auto-drain via
   the `online` event — successfully calls the endpoint and removes the item
   (`pendingCount()` returns to 0). **Do not test this against
   `/add-credit`/`/charge` with real money/balances** given the idempotency
   gap described in item 3.

### 5. Lint (optional but recommended)

```bash
npm run lint
```

---

**Reiterating once more: everything above is unverified draft code.** It was
written carefully and cross-checked by hand against the real backend schema
files, but it has not been installed, compiled, type-checked, linted, or
executed anywhere. Treat this as a draft PR awaiting its first real CI run,
not as finished, working software.
