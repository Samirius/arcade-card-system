<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import { useToast } from 'primevue/usetoast'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const uid = route.params.uid as string
const loading = ref(true)
const card = ref<any>(null)
const transactions = ref<any[]>([])
const activeTab = ref(0)

// Add credit dialog
const showAddCredit = ref(false)
const creditAmount = ref(0)

// Charge dialog
const showCharge = ref(false)
const chargeAmount = ref(0)

async function loadCard() {
  loading.value = true
  try {
    const [cardRes, txRes] = await Promise.all([
      api.get(`/api/v1/cards/${uid}`),
      api.get(`/api/v1/cards/${uid}/transactions`),
    ])
    card.value = cardRes.data
    transactions.value = txRes.data
  } catch {
    toast.add({ severity: 'error', summary: t('common.error'), life: 4000 })
  } finally {
    loading.value = false
  }
}

async function handleAddCredit() {
  if (creditAmount.value <= 0) return
  try {
    await api.post(`/api/v1/cards/${uid}/add-credit`, { amount: creditAmount.value })
    toast.add({ severity: 'success', summary: t('common.success'), life: 3000 })
    showAddCredit.value = false
    creditAmount.value = 0
    await loadCard()
  } catch {
    toast.add({ severity: 'error', summary: t('common.error'), life: 4000 })
  }
}

async function handleCharge() {
  if (chargeAmount.value <= 0) return
  try {
    await api.post(`/api/v1/cards/${uid}/charge`, { amount: chargeAmount.value })
    toast.add({ severity: 'success', summary: t('common.success'), life: 3000 })
    showCharge.value = false
    chargeAmount.value = 0
    await loadCard()
  } catch {
    toast.add({ severity: 'error', summary: t('common.error'), life: 4000 })
  }
}

async function toggleStatus() {
  const endpoint = card.value.status === 'ACTIVE' ? 'deactivate' : 'activate'
  try {
    await api.post(`/api/v1/cards/${uid}/${endpoint}`)
    toast.add({ severity: 'success', summary: t('common.success'), life: 3000 })
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
  <div class="card-detail">
    <PageHeader
      :title="t('card.details')"
      :breadcrumb="[t('card.title'), uid]"
    >
      <template #actions>
        <Button
          :label="t('actions.back')"
          icon="pi pi-arrow-right"
          severity="secondary"
          outlined
          @click="router.push('/admin/cards')"
        />
      </template>
    </PageHeader>

    <div v-if="loading" class="loading-state">
      <i class="pi pi-spinner pi-spin" style="font-size: 2rem" />
    </div>

    <template v-else-if="card">
      <!-- Card Info Card -->
      <div class="card-info-panel">
        <div class="card-info-left">
          <div class="card-uid">{{ card.uid }}</div>
          <div class="card-meta">
            <Tag severity="warning" v-if="card.type === 'VIP'">{{ t('card.types.vip') }}</Tag>
            <Tag severity="info" v-else>{{ t(`card.types.${card.type?.toLowerCase()}`) }}</Tag>
            <Tag :severity="card.status === 'ACTIVE' ? 'success' : 'danger'">
              {{ t(`card.statuses.${card.status?.toLowerCase()}`) }}
            </Tag>
          </div>
          <div v-if="card.customer_name" class="card-customer">
            {{ card.customer_name }}
          </div>
        </div>
        <div class="card-info-right">
          <div class="balance-display">
            <span class="balance-amount">{{ formatAmount(card.balance) }}</span>
            <span class="balance-currency">ج.م</span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="actions-row">
        <Button
          :label="t('cashier.addCredit')"
          icon="pi pi-plus"
          severity="success"
          @click="showAddCredit = true"
        />
        <Button
          :label="t('cashier.charge')"
          icon="pi pi-minus"
          severity="warning"
          @click="showCharge = true"
        />
        <Button
          :label="card.status === 'ACTIVE' ? t('actions.deactivate') : t('actions.activate')"
          icon="pi pi-power-off"
          severity="secondary"
          outlined
          @click="toggleStatus"
        />
      </div>

      <!-- Tabs -->
      <Tabs v-model:active-index="activeTab">
        <TabList>
          <Tab>{{ t('card.transactions') }}</Tab>
          <Tab>{{ t('card.balanceHistory') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            <DataTable :value="transactions" striped-rows :empty-message="t('transaction.noTransactions')">
              <Column field="created_at" :header="t('transaction.date')">
                <template #body="{ data }">
                  {{ new Date(data.created_at).toLocaleString('ar-EG') }}
                </template>
              </Column>
              <Column field="type" :header="t('transaction.type')">
                <template #body="{ data }">
                  <Tag :severity="data.type === 'ADD' ? 'success' : 'warning'">
                    {{ t(`transaction.types.${data.type?.toLowerCase()}`) }}
                  </Tag>
                </template>
              </Column>
              <Column field="amount" :header="t('transaction.amount')">
                <template #body="{ data }">
                  <span :class="['amount', data.type === 'DEDUCT' ? 'deduct' : 'add']">
                    {{ data.type === 'DEDUCT' ? '-' : '+' }}{{ formatAmount(data.amount) }}
                  </span>
                </template>
              </Column>
            </DataTable>
          </TabPanel>
          <TabPanel>
            <div class="empty-tab">
              {{ t('common.noData') }}
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>

    <!-- Add Credit Dialog -->
    <Dialog v-model:visible="showAddCredit" :header="t('cashier.addCredit')" modal>
      <div class="dialog-form">
        <label>{{ t('cashier.enterAmount') }}</label>
        <InputNumber
          v-model="creditAmount"
          mode="decimal"
          :min="0"
          :max="10000"
          autofocus
        />
      </div>
      <template #footer>
        <Button :label="t('actions.cancel')" severity="secondary" outlined @click="showAddCredit = false" />
        <Button :label="t('actions.confirm')" @click="handleAddCredit" />
      </template>
    </Dialog>

    <!-- Charge Dialog -->
    <Dialog v-model:visible="showCharge" :header="t('cashier.charge')" modal>
      <div class="dialog-form">
        <label>{{ t('cashier.enterAmount') }}</label>
        <InputNumber
          v-model="chargeAmount"
          mode="decimal"
          :min="0"
          :max="card?.balance || 0"
          autofocus
        />
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

.card-detail {
  display: flex;
  flex-direction: column;
  gap: $space-5;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: $space-7;
  color: $color-text-muted;
}

.card-info-panel {
  background: linear-gradient(135deg, $color-brand-primary 0%, $color-brand-primary-dark 100%);
  color: white;
  border-radius: $radius-lg;
  padding: $space-6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $space-4;
}

.card-uid {
  font-family: $font-mono;
  font-size: $text-lg;
  margin-bottom: $space-2;
}

.card-meta {
  display: flex;
  gap: $space-2;
  margin-bottom: $space-2;
}

.card-customer {
  font-size: $text-sm;
  opacity: 0.8;
}

.balance-display {
  text-align: center;
}

.balance-amount {
  font-size: $text-4xl;
  font-weight: 700;
  display: block;
  line-height: 1;
}

.balance-currency {
  font-size: $text-base;
  opacity: 0.8;
}

.actions-row {
  display: flex;
  gap: $space-3;
  flex-wrap: wrap;
}

.amount {
  font-weight: 600;
  &.add { color: $color-success; }
  &.deduct { color: $color-danger; }
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: $space-3;
  padding: $space-2 0;
  min-width: 300px;

  label {
    font-weight: 600;
    color: $color-text-secondary;
  }
}

.empty-tab {
  text-align: center;
  padding: $space-6;
  color: $color-text-muted;
}
</style>
