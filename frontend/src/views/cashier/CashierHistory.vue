<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'

const { t } = useI18n()
const loading = ref(true)
const transactions = ref<any[]>([])

async function loadHistory() {
  loading.value = true
  try {
    const res = await api.get('/api/v1/transactions/', { params: { limit: 20 } })
    transactions.value = res.data || []
  } catch { transactions.value = [] } finally { loading.value = false }
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadHistory)
</script>

<template>
  <div class="history-page">
    <h2 class="page-title">{{ t('cashier.todaysTransactions') }}</h2>

    <div v-if="loading" class="loading"><i class="pi pi-spinner pi-spin" style="font-size: 1.5rem" /></div>

    <div v-else-if="!transactions.length" class="empty">{{ t('transaction.noTransactions') }}</div>

    <div v-else class="txn-list">
      <div v-for="txn in transactions" :key="txn.id" class="txn-item">
        <div class="txn-left">
          <span class="txn-uid text-mono">{{ txn.card_uid?.substring(0, 12) }}</span>
          <span class="txn-time">{{ new Date(txn.created_at).toLocaleTimeString('ar-EG') }}</span>
        </div>
        <Tag :severity="txn.type === 'ADD' ? 'success' : 'warning'">
          {{ t(`transaction.types.${txn.type?.toLowerCase() || 'add'}`) }}
        </Tag>
        <span :class="['txn-amount', txn.type === 'DEDUCT' ? 'deduct' : 'add']">
          {{ txn.type === 'DEDUCT' ? '-' : '+' }}{{ formatAmount(txn.amount) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.history-page { display: flex; flex-direction: column; gap: $space-3; }
.page-title { font-size: $text-lg; font-weight: 700; }
.loading, .empty { text-align: center; padding: $space-5; color: $color-text-muted; }

.txn-list { display: flex; flex-direction: column; gap: $space-2; }

.txn-item {
  display: flex; align-items: center; gap: $space-3;
  padding: $space-3; border-radius: $radius-md;
  background: $color-bg-surface; border: 1px solid $color-border;
}

.txn-left { display: flex; flex-direction: column; flex: 1; gap: $space-1; }
.txn-uid { font-size: $text-sm; font-weight: 600; }
.txn-time { font-size: $text-xs; color: $color-text-muted; }

.txn-amount { font-weight: 700; font-size: $text-lg;
  &.add { color: $color-success; }
  &.deduct { color: $color-danger; }
}

.text-mono { font-family: $font-mono; }
</style>
