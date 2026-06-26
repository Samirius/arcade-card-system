<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'primevue/usetoast'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const form = reactive({
  email: '',
  password: '',
})

const submitted = ref(false)

async function handleLogin() {
  submitted.value = true
  if (!form.email || !form.password) return

  try {
    const result = await auth.login(form.email, form.password)
    if (result.mfaRequired) {
      router.push('/verify-mfa')
    } else {
      router.push(auth.redirectAfterLogin())
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: t('auth.invalidCredentials'),
      life: 4000,
    })
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="logo">🧭</div>
        <h1 class="title">{{ t('app.name') }}</h1>
        <p class="subtitle">{{ t('auth.loginSubtitle') }}</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field">
          <label for="email">{{ t('auth.email') }}</label>
          <InputText
            id="email"
            v-model="form.email"
            type="email"
            :placeholder="t('auth.email')"
            :class="{ 'p-invalid': submitted && !form.email }"
            autocomplete="email"
          />
        </div>

        <div class="field">
          <label for="password">{{ t('auth.password') }}</label>
          <Password
            id="password"
            v-model="form.password"
            :feedback="false"
            :placeholder="t('auth.password')"
            :class="{ 'p-invalid': submitted && !form.password }"
            autocomplete="current-password"
            toggle-mask
          />
        </div>

        <Button
          type="submit"
          :label="t('auth.loginButton')"
          :loading="auth.loading"
          class="login-btn"
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

.logo {
  font-size: 3rem;
  margin-bottom: $space-2;
}

.title {
  font-size: $text-3xl;
  font-weight: 700;
  color: $color-brand-primary;
  margin-bottom: $space-1;
}

.subtitle {
  color: $color-text-secondary;
  font-size: $text-base;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: $space-4;
}

.field {
  display: flex;
  flex-direction: column;
  gap: $space-2;

  label {
    font-size: $text-sm;
    font-weight: 600;
    color: $color-text-secondary;
  }
}

.login-btn {
  width: 100%;
  margin-top: $space-2;
}

:deep(.p-inputtext) {
  width: 100%;
}

:deep(.p-password) {
  width: 100%;
}

:deep(.p-password-input) {
  width: 100%;
}
</style>
