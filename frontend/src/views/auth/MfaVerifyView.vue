<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'primevue/usetoast'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const code = ref('')

async function handleVerify() {
  if (code.value.length !== 6) return

  try {
    await auth.verifyMfa(code.value)
    router.push(auth.redirectAfterLogin())
  } catch {
    toast.add({
      severity: 'error',
      summary: t('auth.mfaRequired'),
      life: 4000,
    })
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="logo">🔐</div>
        <h1 class="title">{{ t('auth.mfaCode') }}</h1>
        <p class="subtitle">{{ t('auth.mfaPlaceholder') }}</p>
      </div>

      <form @submit.prevent="handleVerify" class="mfa-form">
        <InputOtp
          v-model="code"
          :length="6"
          integer-only
          class="otp-input"
        />

        <Button
          type="submit"
          :label="t('auth.verifyMfa')"
          :loading="auth.loading"
          class="verify-btn"
        />
      </form>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, $color-brand-primary 0%, $color-brand-primary-dark 100%);
  padding: $space-4;
}

.login-card {
  background: $color-bg-surface;
  border-radius: $radius-lg;
  box-shadow: $shadow-lg;
  padding: $space-7;
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: $space-6;
}

.logo { font-size: 3rem; margin-bottom: $space-2; }

.title {
  font-size: $text-2xl;
  font-weight: 700;
  color: $color-brand-primary;
  margin-bottom: $space-1;
}

.subtitle {
  color: $color-text-secondary;
  font-size: $text-base;
}

.mfa-form {
  display: flex;
  flex-direction: column;
  gap: $space-5;
  align-items: center;
}

.otp-input {
  direction: ltr;
}

.verify-btn {
  width: 100%;
}
</style>
