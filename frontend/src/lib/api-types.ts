/**
 * ⚠️ GENERATED FILE — DO NOT HAND-EDIT.
 *
 * This file is meant to be produced by `openapi-typescript` from the
 * backend's live OpenAPI schema:
 *
 *     npm run gen:api
 *     # runs: openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts
 *
 * It has NOT been generated yet in this environment — `npm install` is
 * blocked here (registry 403), so `openapi-typescript` was never actually
 * installed or executed, and the real backend was never queried. This file
 * is a hand-written PLACEHOLDER so the rest of the codebase has something to
 * import against and so `npm run gen:api` has an obvious target to overwrite
 * once someone runs it on a machine with real npm registry + network access
 * to a running backend.
 *
 * WHAT TO DO NEXT (founder / whoever runs the verified build):
 *   1. `npm install` (pulls in `openapi-typescript` from package.json).
 *   2. Start the backend locally so `/openapi.json` is servable
 *      (`uvicorn app.main:app --reload` or however backend/ is normally run —
 *      default assumed at http://localhost:8000, matching vite.config.ts's
 *      dev proxy target).
 *   3. `npm run gen:api` — this OVERWRITES this entire file with real
 *      generated types (interfaces for every schema in
 *      backend/app/schemas/*, keyed by path+method for every route).
 *   4. Delete the placeholder section below once real types exist; update
 *      any imports that referenced the placeholder shapes to use the real
 *      generated `components["schemas"][...]` types instead.
 *   5. Re-run this whenever backend/app/schemas or backend/app/api routes
 *      change, and commit the regenerated file — treat it like a lockfile,
 *      not like hand-authored source.
 *
 * WHY THIS MATTERS (see FRONTEND_CHANGES.md item 2 for full context):
 * The old approach had `src/config/api.ts` silently rename backend fields
 * on every response (`card_uid` -> `uid`, `owner` -> `customer_name`,
 * `card_type`/`transaction_type` -> `type`) so components could use
 * "nicer" names. That's a silent contract-drift trap: if the backend ever
 * renamed or added a field, nothing would fail loudly — components would
 * just silently receive `undefined` for a field they expect. Generating
 * types directly from the backend's real OpenAPI schema means any drift
 * between frontend expectations and backend reality becomes a TypeScript
 * compile error instead of a runtime "why is this blank" bug.
 *
 * Below are minimal HAND-WRITTEN placeholder shapes (NOT generated, NOT
 * guaranteed to match the live backend exactly) based on reading
 * backend/app/schemas/business.py and backend/app/schemas/transaction.py at
 * authoring time, purely so imports of `@/lib/api-types` don't hard-fail
 * with "module has no exports" before `npm run gen:api` has been run for
 * real. Treat every field here as unverified until regenerated.
 *
 * NOTE: backend/app/schemas/card.py ALSO defines a `CardCreate`/`CardResponse`
 * pair, but backend/app/api/cards.py actually imports its schemas from
 * `app.schemas.business`, not `app.schemas.card` — the shapes below mirror
 * `business.py` (the one actually wired to the live routes), not `card.py`.
 * This is exactly the kind of ambiguity `npm run gen:api` eliminates: it
 * reads the FastAPI app's real OpenAPI schema, not source files that may or
 * may not be the ones actually imported by a given route.
 */

/** Placeholder mirror of backend/app/schemas/business.py CardResponse (the schema actually used by backend/app/api/cards.py). UNVERIFIED. */
export interface PlaceholderCardResponse {
  id: number | null
  card_uid: string
  owner: string
  card_type: 'REGULAR' | 'VIP' | 'STAFF' | 'TEST'
  balance: number
  status: 'ACTIVE' | 'INACTIVE' | 'LOST' | 'STOLEN' | 'DAMAGED'
  created_at: string | null
  updated_at: string | null
}

/** Placeholder mirror of backend/app/schemas/transaction.py TransactionResponse. UNVERIFIED. */
export interface PlaceholderTransactionResponse {
  id: number | null
  card_uid: string
  amount: number
  transaction_type: 'ADD' | 'DEDUCT' | 'REFUND'
  payment_method: 'CASH' | 'CARD' | 'MOBILE' | 'OTHER' | null
  notes: string | null
  created_at: string | null
}

// Once `npm run gen:api` has run for real, this file will instead export
// something like:
//
//   export interface paths { "/api/v1/cards/{card_uid}": { get: { ... } }, ... }
//   export interface components { schemas: { CardResponse: {...}, ... } }
//
// and call sites / openapi-fetch clients should import from those generated
// shapes rather than from the `Placeholder*` interfaces above.
