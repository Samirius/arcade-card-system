import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 15000,
  withCredentials: true, // for httpOnly refresh cookie
})

// --- Request interceptor: attach access token ---
// ⚠️ SECURITY NOTE: Token stored in localStorage is vulnerable to XSS.
// For production hardening, migrate to in-memory token storage with
// httpOnly cookie for refresh token (backend already supports withCredentials).
// See audit item H5 for details.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sindbad-access-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- Response interceptor: normalize card field names ---
function normalizeCardFields(data: any): any {
  if (!data || typeof data !== 'object') return data
  if (Array.isArray(data)) return data.map(normalizeCardFields)
  const normalized = { ...data }
  // Map backend snake_case / different names to frontend expectations
  if ('card_uid' in normalized && !('uid' in normalized)) {
    normalized.uid = normalized.card_uid
  }
  if ('owner' in normalized && !('customer_name' in normalized)) {
    normalized.customer_name = normalized.owner
  }
  if ('card_type' in normalized && !('type' in normalized)) {
    normalized.type = normalized.card_type
  }
  if ('transaction_type' in normalized && !('type' in normalized)) {
    normalized.type = normalized.transaction_type
  }
  return normalized
}

// --- Response interceptor: auto-refresh on 401 ---
let isRefreshing = false
let failedQueue: Array<{ resolve: Function; reject: Function }> = []

function processQueue(error: any, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => {
    // Normalize field names for frontend consumption
    if (response.data) {
      response.data = normalizeCardFields(response.data)
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // If not 401, already retried, or is a login/refresh request — reject immediately
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
        .catch((err) => Promise.reject(err))
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const refreshToken = localStorage.getItem('sindbad-refresh-token')
      const res = await api.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
      const newToken = res.data.access_token
      localStorage.setItem('sindbad-access-token', newToken)

      processQueue(null, newToken)
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return api(originalRequest)
    } catch (refreshErr) {
      processQueue(refreshErr, null)
      // Clear token silently — don't force redirect (let router guard handle it)
      localStorage.removeItem('sindbad-access-token')
      localStorage.removeItem('sindbad-refresh-token')
      delete originalRequest.headers.Authorization
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  }
)
