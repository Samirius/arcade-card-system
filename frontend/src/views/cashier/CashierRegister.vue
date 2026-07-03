<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import { useToast } from 'primevue/usetoast'

const { t } = useI18n()
const router = useRouter()
const toast = useToast()

// FIELD NORMALIZATION REMOVED (see frontend/FRONTEND_CHANGES.md item 2):
// this request body previously sent `uid`/`customer_name`, which do NOT
// match backend/app/schemas/business.py's `CardCreate` schema (it requires
// `card_uid` and `owner`). That was a PRE-EXISTING bug independent of this
// refactor — the old response-normalization layer only ever ran on
// responses, never on outgoing request bodies, so card registration was
// likely already failing (422 from FastAPI/Pydantic for a missing required
// `owner` field) before this patch. Fixed here to send the real field names.
// `form.uid`/`form.customer_name` are kept as the local field/variable names
// (they read fine as UI labels) and mapped to `card_uid`/`owner` at the
// request boundary.
//
// ⚠️ UNRESOLVED GAP (flagging, not guessing a fix): `owner` is a REQUIRED,
// non-empty field on the backend (`Field(..., min_length=1, ...)`), but this
// form's "customer name" input has no required-field validation and can be
// submitted blank, in which case we send `owner: undefined` and the backend
// will very likely reject the request with a 422. This needs a product
// decision during the verified build — either (a) make customer name
// required in this form, or (b) ask the backend team to make `owner`
// optional / accept a default. Not resolved here because guessing the wrong
// one would be worse than leaving it visible.
const form = reactive({
  uid: '',
  card_type: 'REGULAR',
  customer_name: '',
})
const saving = ref(false)

async function handleRegister() {
  if (!form.uid.trim()) return
  saving.value = true
  try {
    const res = await api.post('/api/v1/cards/', {
      card_uid: form.uid,
      card_type: form.card_type,
      owner: form.customer_name || undefined,
    })
    toast.add({ severity: 'success', summary: t('common.success'), life: 3000 })
    router.push(`/cashier/balance/${res.data.card_uid}`)
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
