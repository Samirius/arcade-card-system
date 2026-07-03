<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()
const router = useRouter()

// FIELD NORMALIZATION REMOVED (see frontend/FRONTEND_CHANGES.md item 2):
// reads `transaction_type` directly instead of the previously auto-mapped
// `type`.
const loading = ref(true)
const transactions = ref<any[]>([])

async function loadTransactions() {
  loading.value = true
  try {
    const res = await api.get('/api/v1/transactions/')
    transactions.value = res.data
  } catch {
    transactions.value = []
  } finally {
    loading.value = false
  }
}

const typeSeverity: Record<string, string> = {
  ADD: 'success',
  DEDUCT: 'warning',
  REFUND: 'info',
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadTransactions)
</script>

<template>
  <div class="transactions-view">
    <PageHeader :title="t('transaction.title')" />

    <div class="table-container">
      <DataTable
        :value="transactions"
        :loading="loading"
        striped-rows
        paginator
        :rows="20"
        :empty-message="t('transaction.noTransactions')"
        row-hover
        @row-click="(e: any) => router.push(`/admin/transactions/${e.data.id}`)"
      >
        <Column field="id" :header="t('transaction.id')" class="uid-col">
          <template #body="{ data }">
            {{ data.id?.substring(0, 8) }}
          </template>
        </Column>
        <Column field="created_at" :header="t('transaction.date')">
          <template #body="{ data }">
            {{ new Date(data.created_at).toLocaleString('ar-EG') }}
          </template>
        </Column>
        <Column field="card_uid" :header="t('card.uid')" class="uid-col" />
        <Column field="transaction_type" :header="t('transaction.type')">
          <template #body="{ data }">
            <Tag :severity="typeSeverity[data.transaction_type] || 'info'">
              {{ t(`transaction.types.${data.transaction_type?.toLowerCase() || 'add'}`) }}
            </Tag>
          </template>
        </Column>
        <Column field="amount" :header="t('transaction.amount')">
          <template #body="{ data }">
            <span :class="['amount', data.transaction_type === 'DEDUCT' ? 'deduct' : 'add']">
              {{ data.transaction_type === 'DEDUCT' ? '-' : '+' }}{{ formatAmount(data.amount) }} ج.م
            </span>
          </template>
        </Column>
        <Column field="status" :header="t('transaction.status')">
          <template #body="{ data }">
            <Tag severity="success">{{ t('transaction.statuses.completed') }}</Tag>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.transactions-view {
  display: flex;
  flex-direction: column;
  gap: $space-4;
}

.table-container {
  background: $color-bg-surface;
  border-radius: $radius-lg;
  border: 1px solid $color-border;
  overflow: hidden;
}

.uid-col {
  font-family: $font-mono;
  font-size: $text-sm;
}

.amount {
  font-weight: 600;
  &.add { color: $color-success; }
  &.deduct { color: $color-danger; }
}
</style>
