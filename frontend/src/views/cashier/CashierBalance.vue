<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import { useToast } from 'primevue/usetoast'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()

// FIELD NORMALIZATION REMOVED (see frontend/FRONTEND_CHANGES.md item 2):
// reads raw backend field names (`card.card_uid`, `card.owner`,
// `card.card_type`) instead of the previously auto-mapped
// `uid`/`customer_name`/`type`.
const uid = route.params.uid as string
const loading = ref(true)
const card = ref<any>(null)
const showAddCredit = ref(false)
const showCharge = ref(false)
const amount = ref(0)

async function loadCard() {
  loading.value = true
  try {
    const res = await api.get(`/api/v1/cards/${uid}`)
    card.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: t('common.error'), life: 4000 })
    router.push('/cashier')
  } finally {
    loading.value = false
  }
}

async function handleAddCredit() {
  if (amount.value <= 0) return
  try {
    await api.post(`/api/v1/cards/${uid}/add-credit`, { amount: amount.value })
    toast.add({ severity: 'success', summary: t('cashier.success'), life: 3000 })
    showAddCredit.value = false
    amount.value = 0
    await loadCard()
  } catch {
    toast.add({ severity: 'error', summary: t('common.error'), life: 4000 })
  }
}

async function handleCharge() {
  if (amount.value <= 0) return
  try {
    await api.post(`/api/v1/cards/${uid}/charge`, { amount: amount.value })
    toast.add({ severity: 'success', summary: t('cashier.success'), life: 3000 })
    showCharge.value = false
    amount.value = 0
    await loadCard()
  } catch {
    toast.add({ severity: 'error', summary: t('common.error'), life: 4000 })
  }
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadCard)
</script>

<template>
  <div class="cashier-balance">
    <div v-if="loading" class="loading"><i class="pi pi-spinner pi-spin" style="font-size: 2rem" /></div>

    <template v-else-if="card">
      <!-- Balance Display -->
      <div class="balance-card">
        <div class="card-uid text-mono">{{ card.card_uid }}</div>
        <div v-if="card.owner" class="customer-name">{{ card.owner }}</div>

        <div class="balance-display">
          <div class="balance-label">{{ t('cashier.currentBalance') }}</div>
          <div class="balance-amount">{{ formatAmount(card.balance) }}</div>
          <div class="balance-currency">ج.م</div>
        </div>

        <div class="card-meta">
          <Tag severity="warning" v-if="card.card_type === 'VIP'">VIP</Tag>
          <Tag :severity="card.status === 'ACTIVE' ? 'success' : 'danger'">
            {{ t(`card.statuses.${card.status?.toLowerCase()}`) }}
          </Tag>
        </div>
      </div>

      <!-- Actions -->
      <div class="action-buttons">
        <Button
          :label="t('cashier.addCredit')"
          icon="pi pi-plus"
          severity="success"
          size="large"
          class="action-btn"
          @click="showAddCredit = true; amount = 0"
        />
        <Button
          :label="t('cashier.charge')"
          icon="pi pi-minus"
          severity="warning"
          size="large"
          class="action-btn"
          @click="showCharge = true; amount = 0"
        />
      </div>

      <Button
        :label="t('actions.back')"
        icon="pi pi-arrow-right"
        severity="secondary"
        text
        @click="router.push('/cashier')"
      />
    </template>

    <!-- Add Credit Dialog -->
    <Dialog v-model:visible="showAddCredit" :header="t('cashier.addCredit')" modal :style="{ width: '90%', maxWidth: '400px' }">
      <div class="dialog-form">
        <InputNumber v-model="amount" mode="decimal" :min="0" :max="10000" placeholder="0" :inputStyle="{ fontSize: '2rem', textAlign: 'center' }" autofocus />
      </div>
      <template #footer>
        <Button :label="t('actions.cancel')" severity="secondary" outlined @click="showAddCredit = false" />
        <Button :label="t('actions.confirm')" severity="success" @click="handleAddCredit" />
      </template>
    </Dialog>

    <!-- Charge Dialog -->
    <Dialog v-model:visible="showCharge" :header="t('cashier.charge')" modal :style="{ width: '90%', maxWidth: '400px' }">
      <div class="dialog-form">
        <InputNumber v-model="amount" mode="decimal" :min="0" :max="card?.balance || 0" placeholder="0" :inputStyle="{ fontSize: '2rem', textAlign: 'center' }" autofocus />
      </div>
      <template #footer>
        <Button :label="t('actions.cancel')" severity="secondary" outlined @click="showCharge = false" />
        <Button :label="t('actions.confirm')" severity="warning" @click="handleCharge" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.cashier-balance {
  display: flex;
  flex-direction: column;
  gap: $space-4;
  align-items: center;
}

.loading { padding: $space-7; color: $color-text-muted; }

.balance-card {
  background: linear-gradient(135deg, $color-brand-primary 0%, $color-brand-primary-dark 100%);
  color: white;
  border-radius: $radius-lg;
  padding: $space-6;
  width: 100%;
  text-align: center;
}

.card-uid {
  font-size: $text-sm;
  opacity: 0.8;
  margin-bottom: $space-1;
}

.customer-name {
  font-size: $text-lg;
  font-weight: 600;
  margin-bottom: $space-4;
  opacity: 0.9;
}

.balance-display {
  margin-bottom: $space-4;
}

.balance-label {
  font-size: $text-sm;
  opacity: 0.7;
  margin-bottom: $space-2;
}

.balance-amount {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1;
}

.balance-currency {
  font-size: $text-lg;
  opacity: 0.8;
  margin-top: $space-1;
}

.card-meta {
  display: flex;
  justify-content: center;
  gap: $space-2;
}

.action-buttons {
  display: flex;
  gap: $space-3;
  width: 100%;
}

.action-btn {
  flex: 1;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: $space-4 0;

  :deep(.p-inputnumber) {
    width: 100%;
  }
}

.text-mono { font-family: $font-mono; }
</style>
