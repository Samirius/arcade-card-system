<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'

const { t } = useI18n()
const route = useRoute()
const sidebarCollapsed = ref(false)
</script>

<template>
  <div class="admin-layout">
    <AppSidebar :collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />
    <div class="admin-main">
      <AppTopbar @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed" />
      <main class="admin-content">
        <RouterView :key="route.fullPath" />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.admin-layout {
  display: flex;
  min-height: 100vh;
  background: $color-bg-base;
}

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-content {
  flex: 1;
  padding: $space-6;
  max-width: $content-max-width;
  width: 100%;
  margin: 0 auto;
}
</style>
