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
  <div class="cashier-layout">
    <header class="cashier-topbar">
      <div class="brand">
        <span class="brand-icon">🧭</span>
        <span class="brand-name">{{ t('app.name') }}</span>
      </div>

      <div class="spacer" />

      <button class="lang-toggle" @click="localeStore.toggle()">
        <span v-if="localeStore.isArabic">EN</span>
        <span v-else>ع</span>
      </button>

      <button class="logout-btn" @click="handleLogout">
        <i class="pi pi-sign-out" />
        <span>{{ t('auth.logout') }}</span>
      </button>
    </header>

    <main class="cashier-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.cashier-layout {
  min-height: 100vh;
  background: $color-bg-base;
}

.cashier-topbar {
  height: 56px;
  background: $color-bg-surface;
  border-bottom: 1px solid $color-border;
  display: flex;
  align-items: center;
  padding: 0 $space-4;
  gap: $space-3;
}

.brand {
  display: flex;
  align-items: center;
  gap: $space-2;
}

.brand-icon { font-size: $text-xl; }

.brand-name {
  font-size: $text-lg;
  font-weight: 700;
  color: $color-brand-primary;
}

.spacer { flex: 1; }

.lang-toggle {
  background: $color-bg-muted;
  border: 1px solid $color-border;
  border-radius: $radius-full;
  width: 36px;
  height: 36px;
  font-weight: 700;
  cursor: pointer;
  color: $color-text-primary;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: $space-2;
  background: none;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: $space-2 $space-3;
  cursor: pointer;
  font-family: inherit;
  font-size: $text-sm;
  color: $color-text-secondary;

  &:hover {
    color: $color-danger;
    border-color: $color-danger;
  }
}

.cashier-content {
  padding: $space-4;
  max-width: 600px;
  margin: 0 auto;
}
</style>
