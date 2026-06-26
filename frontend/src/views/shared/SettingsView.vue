<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()
const localeStore = useLocaleStore()
const auth = useAuthStore()
</script>

<template>
  <div class="settings-page">
    <PageHeader :title="t('settings.title')" />

    <div class="settings-section">
      <h3 class="section-title">{{ t('settings.language') }}</h3>
      <div class="lang-options">
        <button
          :class="['lang-btn', { active: localeStore.isArabic }]"
          @click="localeStore.setLocale('ar')"
        >
          العربية
        </button>
        <button
          :class="['lang-btn', { active: !localeStore.isArabic }]"
          @click="localeStore.setLocale('en')"
        >
          English
        </button>
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">{{ t('settings.profile') }}</h3>
      <div class="profile-info">
        <div class="row"><span>الاسم:</span> <strong>{{ auth.user?.full_name || '—' }}</strong></div>
        <div class="row"><span>البريد:</span> <strong>{{ auth.user?.email }}</strong></div>
        <div class="row"><span>الدور:</span> <strong>{{ auth.role }}</strong></div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.settings-page { display: flex; flex-direction: column; gap: $space-5; max-width: 600px; }

.settings-section {
  background: $color-bg-surface;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: $space-5;
}

.section-title { font-size: $text-lg; font-weight: 700; margin-bottom: $space-3; }

.lang-options { display: flex; gap: $space-3; }

.lang-btn {
  padding: $space-3 $space-5;
  border: 2px solid $color-border;
  border-radius: $radius-md;
  background: $color-bg-surface;
  cursor: pointer;
  font-family: inherit;
  font-size: $text-base;
  transition: all $transition-fast;

  &.active {
    border-color: $color-brand-primary;
    color: $color-brand-primary;
    background: $color-brand-primary-50;
  }
}

.profile-info { display: flex; flex-direction: column; gap: $space-3; }
.row { display: flex; gap: $space-2;
  span { color: $color-text-muted; min-width: 60px; }
}
</style>
