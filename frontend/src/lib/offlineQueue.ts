/**
 * Cashier PWA offline command queue.
 *
 * PURPOSE
 * -------
 * When a cashier terminal loses connectivity mid-shift, top-up ("add-credit")
 * and charge actions should still be capturable locally and replayed once
 * the network comes back — instead of the cashier losing the action entirely
 * or being blocked from working. This module is a small, generic,
 * IndexedDB-backed queue of "pending mutating commands" that:
 *
 *   1. `enqueue(kind, endpoint, body)` — persists a command (e.g. a top-up)
 *      to IndexedDB immediately, tagged with a client-generated UUID
 *      idempotency key.
 *   2. `drain(postFn)` — walks the persisted queue in order and POSTs each command
 *      to the backend. **The server response is the source of truth** — this
 *      queue never assumes success; a command is only removed from the queue
 *      after the server confirms it (2xx). Failures are left in the queue
 *      for the next `drain()` call.
 *   3. Registers `online`/`offline` window listeners and auto-drains on
 *      reconnect.
 *
 * This is a SCAFFOLD, not a full offline POS rebuild (per the task brief).
 * It is deliberately generic (`OfflineCommand` is a small envelope, not a
 * union of every possible cashier action) so it can be wired into
 * `CashierBalance.vue`'s add-credit/charge handlers — or elsewhere — with a
 * few lines, without this file needing to know about Vue, Pinia, or the
 * specific dialog components.
 *
 * ⚠️ IDEMPOTENCY — READ BEFORE WIRING THIS INTO REAL MONEY FLOWS:
 * Every queued command carries a client-generated UUID v4 `idempotencyKey`,
 * sent to the backend as an `Idempotency-Key` header (a common, low-friction
 * convention — adjust to whatever the backend team decides to standardize
 * on). *However*, as of this patch, backend/app/api/cards.py's
 * `/cards/{card_uid}/add-credit` and `/cards/{card_uid}/charge` endpoints
 * (see backend/app/schemas/business.py `BalanceOperation`) have NO
 * server-side idempotency-key handling — there is no unique constraint or
 * dedupe lookup keyed on it. That means, until the backend adds idempotency
 * support:
 *   - If a `drain()` POST actually succeeds on the server but the response
 *     is lost (e.g. connection drops right after the server commits the
 *     transaction), retrying the same queued command WILL double-charge or
 *     double-credit the card. The idempotency key is sent defensively (so
 *     wiring it up server-side later is a one-sided backend change), but it
 *     provides NO protection by itself yet.
 *   - Do not enable `drain()` on any real cashier flow in production until
 *     the backend accepts and enforces `Idempotency-Key` (or an equivalent)
 *     on both of those endpoints. Track this as a hard blocker, not a
 *     nice-to-have — this is real cash-drawer money.
 *
 * See frontend/FRONTEND_CHANGES.md item 3 for the full writeup and the
 * example wiring snippet.
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb'

const DB_NAME = 'sindbad-cashier-offline-queue'
const DB_VERSION = 1
const STORE_NAME = 'commands'

/**
 * A single queued mutating action. Kept intentionally generic — `endpoint`
 * + `method` + `body` describe the HTTP call to eventually make; `kind` is
 * a free-form label for UI/debugging (e.g. "add-credit", "charge").
 */
export interface OfflineCommand {
  /** Client-generated UUID v4. Doubles as the queue's primary key and the
   *  value sent as the `Idempotency-Key` header on replay. */
  idempotencyKey: string
  /** Free-form label for display/debugging, e.g. 'add-credit' | 'charge'. */
  kind: string
  /** API path to POST to, e.g. `/api/v1/cards/ABC123/add-credit`. */
  endpoint: string
  /** JSON-serializable request body (amount, notes, etc). */
  body: Record<string, unknown>
  /** Epoch ms when the command was first enqueued (for ordering + display). */
  createdAt: number
  /** Number of drain attempts so far (for backoff/diagnostics). Starts at 0. */
  attempts: number
  /** Last error message from a failed drain attempt, if any. */
  lastError?: string
}

interface OfflineQueueDB extends DBSchema {
  [STORE_NAME]: {
    key: string // idempotencyKey
    value: OfflineCommand
    indexes: { 'by-createdAt': number }
  }
}

let dbPromise: Promise<IDBPDatabase<OfflineQueueDB>> | null = null

function getDB(): Promise<IDBPDatabase<OfflineQueueDB>> {
  if (!dbPromise) {
    dbPromise = openDB<OfflineQueueDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'idempotencyKey' })
        store.createIndex('by-createdAt', 'createdAt')
      },
    })
  }
  return dbPromise
}

/** RFC 4122 v4 UUID. Uses the Web Crypto API (available in all modern
 *  browsers, including in service-worker/PWA contexts) rather than pulling
 *  in a uuid library for one function. */
export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  // Fallback for environments without crypto.randomUUID (very old browsers).
  // Not cryptographically strong, but uniqueness — not secrecy — is what
  // matters for an idempotency key.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Persist a new command to the queue and return it (with its generated
 * idempotency key already attached). Call this immediately when the cashier
 * taps "confirm" on a top-up/charge, BEFORE attempting any network call —
 * that way the action is never lost even if the tab closes right after.
 */
export async function enqueue(
  kind: string,
  endpoint: string,
  body: Record<string, unknown>
): Promise<OfflineCommand> {
  const command: OfflineCommand = {
    idempotencyKey: generateIdempotencyKey(),
    kind,
    endpoint,
    body,
    createdAt: Date.now(),
    attempts: 0,
  }
  const db = await getDB()
  await db.put(STORE_NAME, command)
  return command
}

/** Return all currently-queued commands, oldest first. */
export async function listPending(): Promise<OfflineCommand[]> {
  const db = await getDB()
  return db.getAllFromIndex(STORE_NAME, 'by-createdAt')
}

/** Number of commands currently waiting to be drained. */
export async function pendingCount(): Promise<number> {
  const db = await getDB()
  return db.count(STORE_NAME)
}

async function removeCommand(idempotencyKey: string): Promise<void> {
  const db = await getDB()
  await db.delete(STORE_NAME, idempotencyKey)
}

async function recordFailure(idempotencyKey: string, message: string): Promise<void> {
  const db = await getDB()
  const existing = await db.get(STORE_NAME, idempotencyKey)
  if (!existing) return
  existing.attempts += 1
  existing.lastError = message
  await db.put(STORE_NAME, existing)
}

export interface DrainResult {
  succeeded: OfflineCommand[]
  failed: Array<{ command: OfflineCommand; error: unknown }>
}

/**
 * Attempt to replay every queued command against the API, in the order they
 * were enqueued. A command is removed from the queue ONLY after the server
 * responds with success — the server response is the source of truth, never
 * an optimistic local assumption. Commands that fail stay queued for the
 * next drain (e.g. the next 'online' event, or a manual retry button).
 *
 * `postFn` is injected (rather than importing `@/config/api` directly) so
 * this module has no compile-time dependency on axios/the app's auth setup,
 * and so it stays easy to unit test with a fake poster. In real usage, pass
 * the shared `api` instance's `.post`, e.g.:
 *
 *     import { api } from '@/config/api'
 *     await drain((endpoint, body, headers) => api.post(endpoint, body, { headers }))
 */
export async function drain(
  postFn: (
    endpoint: string,
    body: Record<string, unknown>,
    headers: Record<string, string>
  ) => Promise<unknown>
): Promise<DrainResult> {
  const pending = await listPending()
  const result: DrainResult = { succeeded: [], failed: [] }

  for (const command of pending) {
    try {
      await postFn(command.endpoint, command.body, {
        'Idempotency-Key': command.idempotencyKey,
      })
      await removeCommand(command.idempotencyKey)
      result.succeeded.push(command)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      await recordFailure(command.idempotencyKey, message)
      result.failed.push({ command, error: err })
      // Stop at the first failure rather than hammering the API with every
      // remaining queued command when e.g. the network just dropped again
      // mid-drain. The next 'online' event (or manual retry) will resume
      // from here since failed commands stay in the queue in order.
      break
    }
  }

  return result
}

// --- Online/offline wiring ---------------------------------------------

type ConnectivityListener = (isOnline: boolean) => void
const connectivityListeners = new Set<ConnectivityListener>()

let listenersRegistered = false

/**
 * Register the module-level `online`/`offline` handlers exactly once. Safe
 * to call multiple times (e.g. from multiple components) — subsequent calls
 * are no-ops. Call `onConnectivityChange` separately to observe transitions
 * from application code (e.g. to show a "back online, syncing…" toast).
 */
export function initConnectivityWatcher(postFn: Parameters<typeof drain>[0]): void {
  if (listenersRegistered || typeof window === 'undefined') return
  listenersRegistered = true

  window.addEventListener('online', () => {
    connectivityListeners.forEach((cb) => cb(true))
    // Fire-and-forget: drain whatever is queued now that we're back online.
    // Callers that want to react to the outcome (e.g. show "3 actions
    // synced" / "1 action failed, will retry") should use `drain()`
    // directly instead of relying solely on this auto-drain.
    void drain(postFn)
  })

  window.addEventListener('offline', () => {
    connectivityListeners.forEach((cb) => cb(false))
  })
}

/** Subscribe to online/offline transitions. Returns an unsubscribe function. */
export function onConnectivityChange(listener: ConnectivityListener): () => void {
  connectivityListeners.add(listener)
  return () => connectivityListeners.delete(listener)
}

/** Current browser-reported connectivity. `navigator.onLine` is a best-effort
 *  signal (it does not guarantee the API is actually reachable — e.g. captive
 *  portals report "online" — but it's the standard first-line check). */
export function isOnline(): boolean {
  return typeof navigator === 'undefined' ? true : navigator.onLine
}

/**
 * ---------------------------------------------------------------------
 * EXAMPLE USAGE (not wired into any component by this patch — see
 * frontend/FRONTEND_CHANGES.md item 3 for why, and for the exact
 * before/after diff shape recommended for CashierBalance.vue):
 * ---------------------------------------------------------------------
 *
 *   import { api } from '@/config/api'
 *   import { enqueue, drain, initConnectivityWatcher, isOnline } from '@/lib/offlineQueue'
 *
 *   const postFn = (endpoint: string, body: Record<string, unknown>, headers: Record<string, string>) =>
 *     api.post(endpoint, body, { headers })
 *
 *   initConnectivityWatcher(postFn) // call once, e.g. in CashierLayout.vue onMounted
 *
 *   async function handleAddCredit() {
 *     const endpoint = `/api/v1/cards/${uid}/add-credit`
 *     const body = { amount: amount.value }
 *     if (isOnline()) {
 *       try {
 *         await api.post(endpoint, body) // normal online path, unchanged
 *         return
 *       } catch (err) {
 *         // fall through to queue on network-shaped failures only —
 *         // NOT on 4xx validation errors, which will just fail again.
 *       }
 *     }
 *     await enqueue('add-credit', endpoint, body)
 *     toast.add({ severity: 'warn', summary: 'Saved offline — will sync when back online' })
 *   }
 */
