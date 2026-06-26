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
    const res = await api.get('/api/v1/cards/me/transactions')
    transactions.value = res.data || []
  } catch { transactions.value = [] } finally { loading.value = false }
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadHistory)
</script>

<template>
  <div class="portal-history">
    <h2 class="page-title">{{ t('portal.history') }}</h2>

    <div v-if="loading" class="loading"><i class="pi pi-spinner pi-spin" /></div>
    <div v-else-if="!transactions.length" class="empty">{{ t('portal.noHistory') }}</div>

    <div v-else class="timeline">
      <div v-for="txn in transactions" :key="txn.id" class="timeline-item">
        <div class="timeline-dot" :class="txn.type === 'DEDUCT' ? 'deduct-dot' : 'add-dot'" />
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="txn-type">{{ t(`transaction.types.${txn.type?.toLowerCase() || 'add'}`) }}</span>
            <span :class="['txn-amount', txn.type === 'DEDUCT' ? 'deduct' : 'add']">
              {{ txn.type === 'DEDUCT' ? '-' : '+' }}{{ formatAmount(txn.amount) }} ج.م
            </span>
          </div>
          <span class="txn-date">{{ new Date(txn.created_at).toLocaleString('ar-EG') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.portal-history { display: flex; flex-direction: column; gap: $space-3; }
.page-title { font-size: $text-lg; font-weight: 700; }
.loading, .empty { text-align: center; padding: $space-5; color: $color-text-muted; }

.timeline { display: flex; flex-direction: column; gap: $space-2; }

.timeline-item {
  display: flex; gap: $space-3; padding: $space-3;
  background: $color-bg-surface; border: 1px solid $color-border;
  border-radius: $radius-md;
}

.timeline-dot {
  width: 10px; height: 10px; border-radius: $radius-full;
  margin-top: $space-2; flex-shrink: 0;

  &.add-dot { background: $color-success; }
  &.deduct-dot { background: $color-danger; }
}

.timeline-content { flex: 1; display: flex; flex-direction: column; gap: $space-1; }

.timeline-header {
  display: flex; justify-content: space-between; align-items: center;
}

.txn-type { font-weight: 600; font-size: $text-sm; }
.txn-amount { font-weight: 700;
  &.add { color: $color-success; }
  &.deduct { color: $color-danger; }
}

.txn-date { font-size: $text-xs; color: $color-text-muted; }
</style>
