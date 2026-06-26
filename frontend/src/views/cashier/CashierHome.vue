<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'

const { t } = useI18n()
const router = useRouter()

const searchQuery = ref('')
const recentTxns = ref<any[]>([])

async function searchCard() {
  if (!searchQuery.value.trim()) return
  router.push(`/cashier/balance/${searchQuery.value.trim()}`)
}

async function loadRecent() {
  try {
    const res = await api.get('/api/v1/transactions/', { params: { limit: 5 } })
    recentTxns.value = (res.data || []).slice(0, 5)
  } catch {
    recentTxns.value = []
  }
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadRecent)
</script>

<template>
  <div class="cashier-home">
    <!-- Search -->
    <div class="search-section">
      <h2 class="page-title">{{ t('cashier.title') }}</h2>
      <div class="search-box">
        <InputText
          v-model="searchQuery"
          :placeholder="t('cashier.searchCard')"
          class="search-input"
          @keyup.enter="searchCard"
        />
        <Button
          :label="t('actions.search')"
          icon="pi pi-search"
          @click="searchCard"
        />
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <Button
        :label="t('cashier.registerNew')"
        icon="pi pi-plus"
        severity="success"
        outlined
        class="action-btn"
        @click="router.push('/cashier/register')"
      />
      <Button
        :label="t('cashier.todaysTransactions')"
        icon="pi pi-list"
        severity="info"
        outlined
        class="action-btn"
        @click="router.push('/cashier/history')"
      />
    </div>

    <!-- Recent Transactions -->
    <div class="recent-section" v-if="recentTxns.length">
      <h3 class="section-title">{{ t('cashier.todaysTransactions') }}</h3>
      <div class="txn-list">
        <div v-for="txn in recentTxns" :key="txn.id" class="txn-item">
          <div class="txn-info">
            <span class="txn-uid text-mono">{{ txn.card_uid?.substring(0, 12) }}</span>
            <span class="txn-type">{{ t(`transaction.types.${txn.type?.toLowerCase() || 'add'}`) }}</span>
          </div>
          <span :class="['txn-amount', txn.type === 'DEDUCT' ? 'deduct' : 'add']">
            {{ txn.type === 'DEDUCT' ? '-' : '+' }}{{ formatAmount(txn.amount) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.cashier-home {
  display: flex;
  flex-direction: column;
  gap: $space-5;
}

.page-title {
  font-size: $text-2xl;
  font-weight: 700;
  color: $color-text-primary;
  margin-bottom: $space-3;
}

.search-box {
  display: flex;
  gap: $space-2;
}

.search-input {
  flex: 1;
  font-size: $text-lg;
  padding: $space-3;
}

.quick-actions {
  display: flex;
  gap: $space-3;
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 140px;
}

.recent-section {
  background: $color-bg-surface;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: $space-4;
}

.section-title {
  font-size: $text-base;
  font-weight: 700;
  margin-bottom: $space-3;
  color: $color-text-secondary;
}

.txn-list {
  display: flex;
  flex-direction: column;
  gap: $space-2;
}

.txn-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $space-3;
  border-radius: $radius-md;
  background: $color-bg-muted;
}

.txn-info {
  display: flex;
  flex-direction: column;
  gap: $space-1;
}

.txn-uid {
  font-size: $text-sm;
  font-weight: 600;
}

.txn-type {
  font-size: $text-xs;
  color: $color-text-muted;
}

.txn-amount {
  font-weight: 700;
  font-size: $text-lg;

  &.add { color: $color-success; }
  &.deduct { color: $color-danger; }
}

.text-mono { font-family: $font-mono; }
</style>
