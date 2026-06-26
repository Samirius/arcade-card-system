<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { icon: 'pi-home', labelKey: 'nav.dashboard', to: '/admin/dashboard', roles: ['OWNER', 'ADMIN', 'REGIONAL_MGR'] },
  { icon: 'pi-id-card', labelKey: 'nav.cards', to: '/admin/cards', roles: ['OWNER', 'ADMIN', 'REGIONAL_MGR'] },
  { icon: 'pi-exchange', labelKey: 'nav.transactions', to: '/admin/transactions', roles: ['OWNER', 'ADMIN', 'REGIONAL_MGR'] },
  { icon: 'pi-users', labelKey: 'nav.staff', to: '/admin/staff', roles: ['OWNER', 'ADMIN'], phase2: true },
  { icon: 'pi-map-marker', labelKey: 'nav.locations', to: '/admin/locations', roles: ['OWNER', 'ADMIN'], phase2: true },
  { icon: 'pi-desktop', labelKey: 'nav.machines', to: '/admin/machines', roles: ['OWNER', 'ADMIN'], phase2: true },
  { icon: 'pi-user', labelKey: 'nav.customers', to: '/admin/customers', roles: ['OWNER', 'ADMIN', 'REGIONAL_MGR'], phase2: true },
  { icon: 'pi-wrench', labelKey: 'nav.maintenance', to: '/admin/maintenance', roles: ['OWNER', 'ADMIN'], phase2: true },
  { icon: 'pi-chart-bar', labelKey: 'nav.reports', to: '/admin/reports', roles: ['OWNER', 'ADMIN', 'REGIONAL_MGR'], phase2: true },
]

const visibleItems = computed(() =>
  navItems.filter((item) => !item.roles || item.roles.includes(auth.role || ''))
)

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <aside :class="['app-sidebar', { collapsed }]">
    <div class="sidebar-header">
      <div class="brand">
        <span class="brand-icon">🧭</span>
        <span v-if="!collapsed" class="brand-name">{{ t('app.name') }}</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in visibleItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        active-class="active"
      >
        <i :class="['pi', item.icon]" />
        <span v-if="!collapsed" class="nav-label">{{ t(item.labelKey) }}</span>
        <span v-if="!collapsed && item.phase2" class="phase-badge">Phase 2</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <RouterLink to="/settings" class="nav-item" active-class="active">
        <i class="pi pi-cog" />
        <span v-if="!collapsed" class="nav-label">{{ t('nav.settings') }}</span>
      </RouterLink>
      <button class="nav-item logout-btn" @click="handleLogout">
        <i class="pi pi-sign-out" />
        <span v-if="!collapsed" class="nav-label">{{ t('auth.logout') }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.app-sidebar {
  width: $sidebar-width;
  background: $color-bg-surface;
  border-inline-start: 1px solid $color-border;
  display: flex;
  flex-direction: column;
  transition: width $transition-base;
  flex-shrink: 0;

  &.collapsed {
    width: $sidebar-collapsed;
  }
}

[dir="rtl"] .app-sidebar {
  border-inline-start: none;
  border-inline-end: 1px solid $color-border;
}

.sidebar-header {
  padding: $space-5 $space-4;
  border-bottom: 1px solid $color-border;
}

.brand {
  display: flex;
  align-items: center;
  gap: $space-3;
}

.brand-icon {
  font-size: $text-2xl;
}

.brand-name {
  font-size: $text-xl;
  font-weight: 700;
  color: $color-brand-primary;
}

.sidebar-nav {
  flex: 1;
  padding: $space-3;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: $space-3;
  padding: $space-3 $space-4;
  border-radius: $radius-md;
  color: $color-text-secondary;
  text-decoration: none;
  transition: all $transition-fast;
  margin-bottom: $space-1;
  cursor: pointer;
  border: none;
  background: none;
  width: 100%;
  font-family: inherit;
  font-size: $text-base;

  i {
    font-size: $text-lg;
    flex-shrink: 0;
  }

  &:hover {
    background: $color-bg-hover;
    color: $color-text-primary;
  }

  &.active {
    background: $color-brand-primary-50;
    color: $color-brand-primary;
    font-weight: 600;
  }
}

.phase-badge {
  margin-inline-start: auto;
  font-size: $text-xs;
  padding: 2px $space-2;
  background: $color-bg-muted;
  color: $color-text-muted;
  border-radius: $radius-full;
}

.sidebar-footer {
  padding: $space-3;
  border-top: 1px solid $color-border;
}

.logout-btn:hover {
  color: $color-danger !important;
}
</style>
