<template>
  <div class="not-found">
    <h1>404</h1>
    <p>الصفحة غير موجودة</p>
    <RouterLink to="/login">العودة للرئيسية</RouterLink>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.not-found {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $space-3;

  h1 { font-size: 5rem; font-weight: 800; color: $color-brand-primary; }
  p { color: $color-text-secondary; }
  a { color: $color-brand-primary; font-weight: 600; }
}
</style>
