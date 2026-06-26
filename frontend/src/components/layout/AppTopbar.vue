<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'

const { t } = useI18n()
const auth = useAuthStore()
const localeStore = useLocaleStore()

defineEmits<{ 'toggle-sidebar': [] }>()
</script>

<template>
  <header class="app-topbar">
    <button class="menu-btn" @click="$emit('toggle-sidebar')">
      <i class="pi pi-bars" />
    </button>

    <div class="topbar-spacer" />

    <!-- Language Toggle -->
    <button class="lang-toggle" @click="localeStore.toggle()">
      <span v-if="localeStore.isArabic">EN</span>
      <span v-else>ع</span>
    </button>

    <!-- Profile -->
    <div class="profile">
      <div class="profile-info">
        <span class="profile-name">{{ auth.user?.full_name || auth.user?.email }}</span>
        <span class="profile-role">{{ auth.role }}</span>
      </div>
      <div class="profile-avatar">
        {{ (auth.user?.full_name || auth.user?.email || '?').charAt(0).toUpperCase() }}
      </div>
    </div>
  </header>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.app-topbar {
  height: $topbar-height;
  background: $color-bg-surface;
  border-bottom: 1px solid $color-border;
  display: flex;
  align-items: center;
  padding: 0 $space-5;
  gap: $space-3;
}

.menu-btn {
  background: none;
  border: none;
  font-size: $text-xl;
  cursor: pointer;
  padding: $space-2;
  border-radius: $radius-md;
  color: $color-text-secondary;
  transition: all $transition-fast;

  &:hover {
    background: $color-bg-hover;
  }
}

.topbar-spacer {
  flex: 1;
}

.lang-toggle {
  background: $color-bg-muted;
  border: 1px solid $color-border;
  border-radius: $radius-full;
  width: 40px;
  height: 40px;
  font-weight: 700;
  font-size: $text-sm;
  cursor: pointer;
  color: $color-text-primary;
  transition: all $transition-fast;

  &:hover {
    background: $color-brand-primary-50;
    border-color: $color-brand-primary;
    color: $color-brand-primary;
  }
}

.profile {
  display: flex;
  align-items: center;
  gap: $space-3;
  padding-inline-start: $space-3;
  border-inline-start: 1px solid $color-border;
}

.profile-info {
  display: flex;
  flex-direction: column;
  text-align: end;
}

.profile-name {
  font-size: $text-sm;
  font-weight: 600;
  color: $color-text-primary;
}

.profile-role {
  font-size: $text-xs;
  color: $color-text-muted;
}

.profile-avatar {
  width: 36px;
  height: 36px;
  border-radius: $radius-full;
  background: $color-brand-primary;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: $text-base;
}
</style>
