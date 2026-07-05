<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import { useToast } from 'primevue/usetoast'

const { t } = useI18n()
const router = useRouter()
const toast = useToast()

const form = reactive({
  uid: '',
  card_type: 'REGULAR',
  customer_name: '',
})
const saving = ref(false)

async function handleRegister() {
  // Backend contract (CardCreate): card_uid + owner are REQUIRED.
  if (!form.uid.trim() || !form.customer_name.trim()) {
    toast.add({ severity: 'warn', summary: t('common.error'), detail: t('card.uid') + ' + ' + t('card.customer'), life: 3000 })
    return
  }
  saving.value = true
  try {
    const res = await api.post('/api/v1/cards/', {
      card_uid: form.uid.trim(),
      owner: form.customer_name.trim(),
      card_type: form.card_type,
    })
    toast.add({ severity: 'success', summary: t('common.success'), life: 3000 })
    router.push(`/cashier/balance/${res.data.uid}`)
  } catch (err: any) {
    toast.add({ severity: 'error', summary: err.response?.data?.detail || t('common.error'), life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <h2 class="page-title">{{ t('cashier.registerNew') }}</h2>

    <div class="form-card">
      <div class="field">
        <label>{{ t('card.uid') }}</label>
        <InputText v-model="form.uid" placeholder="04A3B2C1" class="uid-input" />
      </div>

      <div class="field">
        <label>{{ t('card.customer') }}</label>
        <InputText v-model="form.customer_name" :placeholder="t('card.customer')" />
      </div>

      <div class="field">
        <label>{{ t('card.type') }}</label>
        <Select
          v-model="form.card_type"
          :options="[
            { label: t('card.types.regular'), value: 'REGULAR' },
            { label: t('card.types.vip'), value: 'VIP' },
            { label: t('card.types.staff'), value: 'STAFF' },
            { label: t('card.types.test'), value: 'TEST' },
          ]"
          option-label="label"
          option-value="value"
        />
      </div>

      <Button
        :label="t('actions.register')"
        icon="pi pi-check"
        :loading="saving"
        @click="handleRegister"
        class="submit-btn"
      />
    </div>

    <Button :label="t('actions.back')" icon="pi pi-arrow-right" severity="secondary" text @click="router.push('/cashier')" />
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.register-page { display: flex; flex-direction: column; gap: $space-4; align-items: center; }
.page-title { font-size: $text-xl; font-weight: 700; margin-bottom: $space-2; }

.form-card {
  background: $color-bg-surface;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: $space-5;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: $space-4;
}

.field { display: flex; flex-direction: column; gap: $space-2;
  label { font-size: $text-sm; font-weight: 600; color: $color-text-secondary; }
}

.uid-input { font-family: $font-mono; }

.submit-btn { width: 100%; margin-top: $space-2; }
</style>
