<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  title: string
  breadcrumb?: string[]
}>()
</script>

<template>
  <div class="page-header">
    <h1 class="page-title">{{ title }}</h1>
    <div v-if="breadcrumb && breadcrumb.length" class="breadcrumb">
      <span v-for="(crumb, i) in breadcrumb" :key="i" class="crumb">
        <i v-if="i > 0" class="pi pi-chevron-left separator" />
        {{ crumb }}
      </span>
    </div>
    <div class="actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.page-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $space-3;
  margin-bottom: $space-5;
}

.page-title {
  font-size: $text-2xl;
  font-weight: 700;
  color: $color-text-primary;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: $space-2;
  font-size: $text-sm;
  color: $color-text-muted;
  margin-inline-start: $space-2;
}

.crumb {
  display: inline-flex;
  align-items: center;
  gap: $space-2;
}

.separator {
  font-size: $text-xs;
  color: $color-text-muted;
}

.actions {
  margin-inline-start: auto;
  display: flex;
  gap: $space-2;
}
</style>
