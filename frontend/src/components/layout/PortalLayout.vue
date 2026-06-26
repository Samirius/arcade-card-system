<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const localeStore = useLocaleStore()
const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="portal-layout">
    <header class="portal-topbar">
      <div class="brand">
        <span class="brand-icon">🧭</span>
        <span class="brand-name">{{ t('app.name') }}</span>
      </div>
      <div class="spacer" />
      <button class="lang-toggle" @click="localeStore.toggle()">
        <span v-if="localeStore.isArabic">EN</span>
        <span v-else>ع</span>
      </button>
    </header>

    <main class="portal-content">
      <RouterView />
    </main>

    <nav class="portal-bottomnav">
      <RouterLink to="/portal/balance" active-class="active">
        <i class="pi pi-wallet" />
        <span>{{ t('portal.balance') }}</span>
      </RouterLink>
      <RouterLink to="/portal/history" active-class="active">
        <i class="pi pi-list" />
        <span>{{ t('portal.history') }}</span>
      </RouterLink>
      <button class="nav-btn" @click="handleLogout">
        <i class="pi pi-sign-out" />
        <span>{{ t('auth.logout') }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.portal-layout {
  min-height: 100vh;
  background: $color-bg-base;
  padding-bottom: 70px;
}

.portal-topbar {
  height: 52px;
  background: $color-bg-surface;
  border-bottom: 1px solid $color-border;
  display: flex;
  align-items: center;
  padding: 0 $space-4;
  gap: $space-2;
}

.brand {
  display: flex;
  align-items: center;
  gap: $space-2;
}

.brand-icon { font-size: $text-lg; }

.brand-name {
  font-size: $text-base;
  font-weight: 700;
  color: $color-brand-primary;
}

.spacer { flex: 1; }

.lang-toggle {
  background: $color-bg-muted;
  border: 1px solid $color-border;
  border-radius: $radius-full;
  width: 32px;
  height: 32px;
  font-weight: 700;
  font-size: $text-xs;
  cursor: pointer;
}

.portal-content {
  padding: $space-4;
  max-width: 420px;
  margin: 0 auto;
}

.portal-bottomnav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: $color-bg-surface;
  border-top: 1px solid $color-border;
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: $z-sticky;

  a, .nav-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $space-1;
    background: none;
    border: none;
    font-family: inherit;
    font-size: $text-xs;
    color: $color-text-muted;
    cursor: pointer;
    padding: $space-2;
    text-decoration: none;
    transition: color $transition-fast;

    i { font-size: $text-xl; }

    &.active, &:hover {
      color: $color-brand-primary;
    }
  }
}
</style>
