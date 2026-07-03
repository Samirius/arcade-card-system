import axios from 'axios'
import { getAccessToken, setAccessToken, clearAccessToken } from '@/lib/tokenStore'

/**
 * Shared axios instance for all API calls.
 *
 * CHANGE LOG (see frontend/FRONTEND_CHANGES.md for the full writeup):
 *  1. Access token storage moved from `localStorage` to an in-memory singleton
 *     (`@/lib/tokenStore`). See that file for the detailed rationale and the
 *     BACKEND CONTRACT REQUIREMENT this depends on (httpOnly refresh cookie).
 *  2. The snake_case -> camelCase / renamed-field normalization layer
 *     (`normalizeCardFields`) that used to run on every response has been
 *     REMOVED. Call sites now receive raw backend field names
 *     (`card_uid`, `owner`, `card_type`, `transaction_type`, ...) exactly as
 *     FastAPI/Pydantic serializes them. See FRONTEND_CHANGES.md for the list
 *     of components that relied on the old mapped names and still need to be
 *     migrated/verified against a real backend.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 15000,
  // Required so the browser sends/receives the httpOnly refresh cookie.
  // NOTE: the backend must respond with a matching `Access-Control-Allow-
  // Credentials: true` header and an explicit (non-wildcard) allowed origin
  // for this to actually carry the cookie cross-origin. See tokenStore.ts.
  withCredentials: true,
})

// --- Request interceptor: attach in-memory access token ---
// No localStorage read here anymore. If there is no in-memory token (e.g.
// fresh page load, or the in-memory value was cleared), the request goes out
// without an Authorization header and the backend will (correctly) 401 it;
// the response interceptor below then attempts a cookie-based refresh.
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- Response interceptor: auto-refresh on 401, single-flight ---
//
// Single-flight refresh: if N requests fail with 401 concurrently, only the
// first one triggers a POST /auth/refresh call. The rest are queued and
// re-dispatched with the new token once that single refresh resolves (or
// rejected together if it fails). This avoids a thundering herd of parallel
// refresh calls (which, depending on backend refresh-token rotation, could
// also race each other into invalidating one another's tokens).
let refreshPromise: Promise<string> | null = null

function performRefresh(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = api
      .post('/api/v1/auth/refresh', {}) // no body: refresh token travels via httpOnly cookie only
      .then((res) => {
        const newToken = res.data?.access_token
        if (!newToken) {
          throw new Error('Refresh response did not include access_token')
        }
        setAccessToken(newToken)
        return newToken as string
      })
      .catch((err) => {
        // Refresh failed (cookie missing/expired/revoked) — clear whatever
        // in-memory token we had so the app treats the user as logged out.
        clearAccessToken()
        throw err
      })
      .finally(() => {
        // Reset so the *next* 401 (e.g. after the user logs back in) starts
        // a fresh single-flight cycle instead of reusing a settled promise.
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If not 401, already retried once, or is itself an auth request —
    // reject immediately. Retrying /auth/refresh or /auth/login here would
    // either loop forever or mask the real login failure.
    if (
      !originalRequest ||
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      const newToken = await performRefresh()
      originalRequest.headers = originalRequest.headers || {}
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return api(originalRequest)
    } catch (refreshErr) {
      return Promise.reject(refreshErr)
    }
  }
)
