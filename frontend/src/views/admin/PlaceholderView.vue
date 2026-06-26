<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()
const route = useRoute()

const titleKey = String(route.meta.title || 'nav.dashboard')
</script>

<template>
  <div>
    <PageHeader :title="t(titleKey)" />
    <div class="placeholder">
      <i class="pi pi-hourglass" style="font-size: 3rem" />
      <h2>Phase 2 — Coming Soon</h2>
      <p>هذه الوحدة قيد التطوير وستكون متاحة في المرحلة الثانية</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.placeholder {
  text-align: center;
  padding: $space-7;
  color: $color-text-muted;

  i { margin-bottom: $space-4; }
  h2 { font-size: $text-xl; margin-bottom: $space-2; color: $color-text-secondary; }
  p { font-size: $text-base; }
}
</style>
