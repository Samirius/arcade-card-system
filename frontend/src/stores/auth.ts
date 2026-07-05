import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, setAuthToken, onTokenRefresh } from '@/config/api'

export interface User {
  id: string
  email: string
  full_name: string
  role: 'STAFF' | 'SUPERVISOR' | 'REGIONAL_MGR' | 'ADMIN' | 'OWNER' | 'CUSTOMER'
  status: string
  company_id?: string
  mfa_enabled: boolean
}

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
    setAuthToken(token)
  }

  function clearToken() {
    accessToken.value = null
    setAuthToken(null)
  }

  // Keep the store in sync when the axios layer silently refreshes (or drops) the token.
  onTokenRefresh((token) => {
    accessToken.value = token
  })

  // Session restore runs once per app load. Tokens are held in memory only;
  // the httpOnly refresh cookie (set by the backend on login) is the sole
  // persistent credential — nothing is ever written to localStorage.
  let initPromise: Promise<void> | null = null
  function init(): Promise<void> {
    if (!initPromise) {
      initPromise = (async () => {
        try {
          const res = await api.post('/api/v1/auth/refresh', {})
          if (res.data?.access_token) {
            setToken(res.data.access_token)
            user.value = normalizeUser(res.data.user)
          }
        } catch {
          // No valid refresh cookie — stay logged out; router guard redirects.
        }
      })()
    }
    return initPromise
  }

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post('/api/v1/auth/login', { email, password })
      // Backend returns 'requires_mfa' (read 'mfa_required' too, defensively).
      // NOTE: local name must NOT shadow the `mfaRequired` ref above.
      const needsMfa = res.data.mfa_required ?? res.data.requires_mfa ?? false
      if (needsMfa) {
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
