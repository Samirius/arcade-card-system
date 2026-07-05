<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useLocaleStore } from '@/stores/locale'
import { useAuthStore } from '@/stores/auth'

const localeStore = useLocaleStore()
const authStore = useAuthStore()

const direction = computed(() => (localeStore.isArabic ? 'rtl' : 'ltr'))
const localeClass = computed(() => (localeStore.isArabic ? 'locale-ar' : 'locale-en'))

onMounted(() => {
  // Restore saved language (sets dir/lang on <html>) and session on refresh
  localeStore.init()
  authStore.init()
})
</script>

<template>
  <div :dir="direction" :class="localeClass" class="app-root">
    <RouterView />
    <Toast position="top-left" />
    <ConfirmDialog />
  </div>
</template>

<style scoped>
.app-root {
  min-height: 100vh;
}
</style>
