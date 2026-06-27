import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // --- Auth ---
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/verify-mfa',
      name: 'verify-mfa',
      component: () => import('@/views/auth/MfaVerifyView.vue'),
      meta: { guestOnly: true },
    },

    // --- Admin Surface ---
    {
      path: '/admin',
      component: () => import('@/components/layout/AdminLayout.vue'),
      meta: { requiresAuth: true, roles: ['OWNER', 'ADMIN', 'REGIONAL_MGR'] },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue') },
        { path: 'cards', name: 'admin-cards', component: () => import('@/views/admin/CardsView.vue') },
        { path: 'cards/:uid', name: 'admin-card-detail', component: () => import('@/views/admin/CardDetailView.vue') },
        { path: 'transactions', name: 'admin-transactions', component: () => import('@/views/admin/TransactionsView.vue') },
        { path: 'transactions/:id', name: 'admin-transaction-detail', component: () => import('@/views/admin/TransactionDetailView.vue') },
        // Phase 2 stubs
        { path: 'staff', name: 'admin-staff', component: () => import('@/views/admin/PlaceholderView.vue'), meta: { title: 'nav.staff', icon: 'pi-users' } },
        { path: 'locations', name: 'admin-locations', component: () => import('@/views/admin/PlaceholderView.vue'), meta: { title: 'nav.locations', icon: 'pi-map-marker' } },
        { path: 'machines', name: 'admin-machines', component: () => import('@/views/admin/PlaceholderView.vue'), meta: { title: 'nav.machines', icon: 'pi-desktop' } },
        { path: 'customers', name: 'admin-customers', component: () => import('@/views/admin/PlaceholderView.vue'), meta: { title: 'nav.customers', icon: 'pi-id-card' } },
        { path: 'maintenance', name: 'admin-maintenance', component: () => import('@/views/admin/PlaceholderView.vue'), meta: { title: 'nav.maintenance', icon: 'pi-wrench' } },
        { path: 'reports', name: 'admin-reports', component: () => import('@/views/admin/PlaceholderView.vue'), meta: { title: 'nav.reports', icon: 'pi-chart-bar' } },
      ],
    },

    // --- Cashier Surface ---
    {
      path: '/cashier',
      component: () => import('@/components/layout/CashierLayout.vue'),
      meta: { requiresAuth: true, roles: ['STAFF', 'SUPERVISOR', 'ADMIN', 'OWNER'] },
      children: [
        { path: '', name: 'cashier-home', component: () => import('@/views/cashier/CashierHome.vue') },
        { path: 'balance/:uid', name: 'cashier-balance', component: () => import('@/views/cashier/CashierBalance.vue') },
        { path: 'register', name: 'cashier-register', component: () => import('@/views/cashier/CashierRegister.vue') },
        { path: 'history', name: 'cashier-history', component: () => import('@/views/cashier/CashierHistory.vue') },
      ],
    },

    // --- Customer Portal ---
    {
      path: '/portal',
      component: () => import('@/components/layout/PortalLayout.vue'),
      meta: { requiresAuth: true, roles: ['CUSTOMER'] },
      children: [
        { path: '', redirect: '/portal/balance' },
        { path: 'balance', name: 'portal-balance', component: () => import('@/views/portal/PortalBalance.vue') },
        { path: 'history', name: 'portal-history', component: () => import('@/views/portal/PortalHistory.vue') },
      ],
    },

    // --- Shared ---
    { path: '/settings', name: 'settings', component: () => import('@/views/shared/SettingsView.vue'), meta: { requiresAuth: true } },
    { path: '/403', name: 'unauthorized', component: () => import('@/views/shared/UnauthorizedView.vue') },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/shared/NotFoundView.vue') },
    { path: '/', redirect: '/login' },
  ],
})

// --- Navigation Guard ---
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // Initialize auth if not done yet
  if (!auth.isAuthenticated && !to.meta.guestOnly) {
    await auth.init()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next('/login')
  }

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return next(auth.redirectAfterLogin())
  }

  // Role check
  if (to.meta.roles && auth.isAuthenticated) {
    const userRole = auth.role
    const allowedRoles = to.meta.roles as string[]
    if (userRole && !allowedRoles.includes(userRole)) {
      return next(auth.redirectAfterLogin())
    }
  }

  next()
})

export default router
