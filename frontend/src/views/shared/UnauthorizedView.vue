<template>
  <div class="unauthorized">
    <h1>403</h1>
    <p>ليس لديك صلاحية للوصول لهذه الصفحة</p>
    <RouterLink to="/login">العودة للرئيسية</RouterLink>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.unauthorized {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $space-3;

  h1 { font-size: 5rem; font-weight: 800; color: $color-danger; }
  p { color: $color-text-secondary; }
  a { color: $color-brand-primary; font-weight: 600; }
}
</style>
