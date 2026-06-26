<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  suffix?: string
  icon: string
  color?: 'primary' | 'success' | 'accent' | 'info'
  loading?: boolean
}>(), {
  color: 'primary',
  loading: false,
})

const colorMap = {
  primary: '#0D9488',
  success: '#22C55E',
  accent: '#F59E0B',
  info: '#3B82F6',
}

const bgColor = computed(() => colorMap[props.color])
</script>

<template>
  <div class="stat-card" :class="{ loading }">
    <div class="stat-icon" :style="{ background: bgColor + '20', color: bgColor }">
      <i :class="['pi', icon]" />
    </div>
    <div class="stat-body">
      <div class="stat-label">{{ label }}</div>
      <div v-if="loading" class="stat-skeleton" />
      <div v-else class="stat-value">
        {{ value }}
        <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.stat-card {
  background: $color-bg-surface;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: $space-5;
  display: flex;
  align-items: center;
  gap: $space-4;
  transition: box-shadow $transition-fast;

  &:hover {
    box-shadow: $shadow-md;
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  i {
    font-size: $text-xl;
  }
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: $text-sm;
  color: $color-text-secondary;
  margin-bottom: $space-1;
}

.stat-value {
  font-size: $text-3xl;
  font-weight: 700;
  color: $color-text-primary;
  line-height: 1.2;
}

.stat-suffix {
  font-size: $text-base;
  font-weight: 500;
  color: $color-text-muted;
  margin-inline-start: $space-1;
}

.stat-skeleton {
  height: 32px;
  width: 80px;
  background: $color-bg-muted;
  border-radius: $radius-sm;
  animation: pulse 1.5s ease infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
