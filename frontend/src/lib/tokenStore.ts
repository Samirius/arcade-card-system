/**
 * In-memory access token store.
 *
 * WHY THIS EXISTS (security context — see audit item H5):
 * The access token used to be persisted to `localStorage` (`sindbad-access-token`).
 * Anything readable by JavaScript in the page's origin — including this key — is
 * readable by an XSS payload, which turns a single injected script into a full
 * account takeover with a long-lived bearer token. Storing the access token only
 * in a JS module variable (never in localStorage/sessionStorage, never in a
 * non-httpOnly cookie) means an XSS payload can still *use* the token for the
 * lifetime of the page, but it can no longer *exfiltrate and replay it later* —
 * the token disappears on tab close/reload and is never written to disk.
 *
 * This module is a plain singleton (not a Pinia store) so it can be imported by
 * both `src/config/api.ts` (the axios interceptor, which must not depend on
 * Pinia being installed yet) and `src/stores/auth.ts` without a circular
 * dependency between the store and the HTTP client.
 *
 * ⚠️ BACKEND CONTRACT REQUIREMENT (coordinated change — NOT done by this patch):
 * In-memory-only access tokens are only viable if the refresh token lives in an
 * httpOnly, Secure, SameSite=strict|lax cookie that the browser attaches
 * automatically. Today (see backend/app/api/auth.py) `/auth/login`,
 * `/auth/login/mfa`, and `/auth/refresh` return `refresh_token` in the *JSON
 * body* and never call `response.set_cookie(...)`. That means, as of this
 * patch, there is NO refresh cookie yet — the frontend change alone is
 * necessary but not sufficient. The backend team must:
 *   1. On successful /auth/login, /auth/login/mfa, and /auth/refresh, set an
 *      httpOnly + Secure + SameSite cookie (e.g. `refresh_token`) instead of
 *      (or in addition to, during migration) returning it in the response
 *      body.
 *   2. Stop returning `refresh_token` in the JSON body once the frontend
 *      migration above is confirmed deployed (leaving it in the body defeats
 *      the whole point — it becomes reachable by JS/XSS again).
 *   3. Ensure `/auth/refresh` reads the cookie via `request.cookies.get(...)`
 *      (it already supports this as a fallback — see auth.py — but should
 *      become the *primary* path) and continues to rotate/invalidate refresh
 *      tokens server-side as it does today.
 *   4. Confirm CORS is configured with `allow_credentials=True` and an exact
 *      (non-wildcard) `allow_origins` list, since cookies are not sent on
 *      cross-origin requests with `Access-Control-Allow-Origin: *`.
 * Until that backend change ships, this in-memory store still "works" in the
 * sense that the access token never touches localStorage, but every full page
 * reload will log the user out (no cookie to silently refresh from), and the
 * 401-refresh flow in `src/config/api.ts` will fail because there is no
 * refresh token available to the backend. That is expected and acceptable
 * during the migration window — do not work around it by putting the refresh
 * token back into localStorage.
 */

let accessToken: string | null = null

/** Read the current in-memory access token, if any. */
export function getAccessToken(): string | null {
  return accessToken
}

/** Store a new access token in memory (never persisted to disk). */
export function setAccessToken(token: string | null): void {
  accessToken = token
}

/** Clear the in-memory access token (logout, refresh failure, etc). */
export function clearAccessToken(): void {
  accessToken = null
}

/** Convenience boolean used by call sites that just need presence/absence. */
export function hasAccessToken(): boolean {
  return accessToken !== null
}
