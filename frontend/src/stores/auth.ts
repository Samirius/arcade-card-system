import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/config/api'
import { setAccessToken, clearAccessToken } from '@/lib/tokenStore'

export interface User {
  id: string
  email: string
  full_name: string
  role: 'STAFF' | 'SUPERVISOR' | 'REGIONAL_MGR' | 'ADMIN' | 'OWNER' | 'CUSTOMER'
  status: string
  company_id?: string
  mfa_enabled: boolean
}

/**
 * NOTE ON NORMALIZATION: this is intentionally NOT the same thing as the
 * `normalizeCardFields` shim that was removed from `src/config/api.ts`.
 * That shim silently renamed backend fields (`card_uid` -> `uid`, `owner` ->
 * `customer_name`, ...) to paper over a frontend/backend contract mismatch,
 * which is exactly what the OpenAPI-generated typed client
 * (`src/lib/api-types.ts`, `npm run gen:api`) is meant to make impossible to
 * miss going forward.
 *
 * `normalizeUser` below is different: the backend genuinely returns
 * `first_name` + `last_name` as two separate fields (see
 * backend/app/api/auth.py `/login`, `/login/mfa`, `/me`), and there is no
 * single `full_name` field to rename from — this is a real UI-convenience
 * derivation, not a rename. It is kept as-is. If/when the backend adds a
 * computed `full_name` to its response, this can be simplified to read it
 * directly.
 */
function normalizeUser(raw: any): User {
  return {
    id: raw.id,
    email: raw.email,
    full_name: raw.full_name || [raw.first_name, raw.last_name].filter(Boolean).join(' ') || raw.email,
    role: raw.role,
    status: raw.status,
    company_id: raw.company_id,
    mfa_enabled: raw.mfa_enabled ?? false,
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  // `accessToken` stays as a ref purely so components/router-guards can
  // reactively read `isAuthenticated` etc. The actual token VALUE used for
  // outgoing requests lives only in `@/lib/tokenStore` (in-memory, not
  // localStorage) — this ref mirrors that value for reactivity but is not
  // itself the source of truth read by the axios interceptor.
  const accessToken = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const mfaRequired = ref(false)
  const pendingEmail = ref<string | null>(null)
  const pendingPassword = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)
  const role = computed(() => user.value?.role || null)
  const isAdmin = computed(() =>
    ['OWNER', 'ADMIN', 'REGIONAL_MGR'].includes(role.value || '')
  )
  const isCashier = computed(() =>
    ['STAFF', 'SUPERVISOR', 'ADMIN', 'OWNER'].includes(role.value || '')
  )
  const isCustomer = computed(() => role.value === 'CUSTOMER')

  function setToken(token: string) {
    accessToken.value = token
    setAccessToken(token)
    // No `api.defaults.headers.common['Authorization']` assignment anymore —
    // the request interceptor in `@/config/api.ts` reads the token fresh
    // from the in-memory store on every request, so there is nothing to
    // keep in sync here.
  }

  function clearToken() {
    accessToken.value = null
    clearAccessToken()
  }

  async function init() {
    // TOKEN STORAGE FIX: previously this gated session restore on
    // `localStorage.getItem('sindbad-access-token')` — i.e. it would only
    // ever try to restore a session if a *plaintext* access token had been
    // persisted to disk on a prior visit. Since the access token is now
    // in-memory only (see @/lib/tokenStore), that check is gone by
    // construction: there is nothing in localStorage to check, and on a
    // fresh page load the in-memory token is always empty.
    //
    // Instead, we unconditionally attempt a cookie-based refresh. If the
    // browser is holding a valid httpOnly refresh cookie, this silently
    // restores the session (new access token + user). If there is no cookie
    // (or it's expired/revoked), this call 401s/errors and we fall through
    // to "logged out" — which is the correct behavior.
    //
    // ⚠️ Depends on the backend actually setting that httpOnly cookie on
    // login — see the BACKEND CONTRACT REQUIREMENT note in
    // @/lib/tokenStore.ts. Until that ships, `init()` will always fail here
    // and every full page reload will require a fresh login. That is
    // expected during the migration window.
    try {
      const res = await api.post('/api/v1/auth/refresh', {})
      if (res.data?.access_token) {
        setToken(res.data.access_token)
        user.value = normalizeUser(res.data.user)
      }
    } catch {
      clearToken()
    }
  }

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post('/api/v1/auth/login', { email, password })
      // Backend returns `requires_mfa` (see backend/app/api/auth.py); some
      // older frontend code paths also checked `mfa_required`. Kept as a
      // dual-read for safety, but this is worth confirming against the real
      // OpenAPI schema (`npm run gen:api`) during the verified build —
      // if `mfa_required` is never actually sent by the backend, drop it.
      const requiresMfa = res.data.mfa_required ?? res.data.requires_mfa ?? false
      if (requiresMfa) {
        mfaRequired.value = true
        pendingEmail.value = email
        pendingPassword.value = password
        return { mfaRequired: true }
      }
      setToken(res.data.access_token)
      user.value = normalizeUser(res.data.user)
      return { mfaRequired: false }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function verifyMfa(code: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post('/api/v1/auth/login/mfa', {
        email: pendingEmail.value,
        password: pendingPassword.value,
        mfa_code: code,
      })
      setToken(res.data.access_token)
      user.value = normalizeUser(res.data.user)
      mfaRequired.value = false
      pendingEmail.value = null
      pendingPassword.value = null
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'MFA verification failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    try {
      const res = await api.get('/api/v1/auth/me')
      user.value = normalizeUser(res.data)
    } catch {
      clearToken()
    }
  }

  async function logout() {
    try {
      await api.post('/api/v1/auth/logout', {})
    } catch {
      // ignore
    }
    clearToken()
    user.value = null
  }

  function redirectAfterLogin(): string {
    if (isAdmin.value) return '/admin/dashboard'
    if (isCashier.value) return '/cashier'
    if (isCustomer.value) return '/portal/balance'
    return '/admin/dashboard'
  }

  return {
    user, accessToken, loading, error, mfaRequired,
    isAuthenticated, role, isAdmin, isCashier, isCustomer,
    init, login, verifyMfa, fetchUser, logout, redirectAfterLogin,
    setToken, clearToken,
  }
})
