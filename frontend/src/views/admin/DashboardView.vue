<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import StatCard from '@/components/ui/StatCard.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()

const loading = ref(true)
// Field names match the backend /dashboard/stats contract exactly.
const stats = ref({
  revenue_today: 0,
  cards_active: 0,
  transactions_today: 0,
  cards_total: 0,
})
const recentTransactions = ref<any[]>([])
const revenueData = ref<{ labels: string[]; values: number[] }>({ labels: [], values: [] })

async function loadData() {
  loading.value = true
  try {
    const [statsRes, recentRes, revenueRes] = await Promise.all([
      api.get('/api/v1/dashboard/stats'),
      api.get('/api/v1/dashboard/transactions/recent?limit=10'),
      api.get('/api/v1/dashboard/revenue?days=7'),
    ])
    stats.value = statsRes.data
    recentTransactions.value = recentRes.data
    // /dashboard/revenue returns an OBJECT: { period, by_day: [{date, revenue}], ... }
    const byDay = revenueRes.data?.by_day ?? []
    revenueData.value = {
      labels: byDay.map((r: any) => r.date),
      values: byDay.map((r: any) => Number(r.revenue)),
    }
  } catch (err) {
    // Handle gracefully
  } finally {
    loading.value = false
  }
}

function formatAmount(amount: number | string) {
  // Backend serializes DECIMAL as string — coerce before formatting.
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(Number(amount) || 0)
}

onMounted(loadData)
</script>

<template>
  <div class="dashboard">
    <PageHeader :title="t('dashboard.title')" />

    <!-- Stats Row -->
    <div class="stats-grid">
      <StatCard
        :label="t('dashboard.revenueToday')"
        :value="formatAmount(stats.revenue_today)"
        suffix="ج.م"
        icon="pi-money-bill"
        color="success"
        :loading="loading"
      />
      <StatCard
        :label="t('dashboard.activeCards')"
        :value="stats.cards_active"
        icon="pi-id-card"
        color="primary"
        :loading="loading"
      />
      <StatCard
        :label="t('dashboard.transactionsToday')"
        :value="stats.transactions_today"
        icon="pi-exchange"
        color="accent"
        :loading="loading"
      />
      <StatCard
        :label="t('dashboard.cardsIssued')"
        :value="stats.cards_total"
        icon="pi-credit-card"
        color="info"
        :loading="loading"
      />
    </div>

    <!-- Recent Transactions -->
    <div class="recent-section">
      <h2 class="section-title">{{ t('dashboard.recentTransactions') }}</h2>
      <div v-if="recentTransactions.length === 0 && !loading" class="empty">
        {{ t('dashboard.noTransactions') }}
      </div>
      <DataTable v-else :value="recentTransactions" :loading="loading" striped-rows>
        <Column field="date" :header="t('transaction.date')">
          <template #body="{ data }">
            {{ new Date(data.created_at || data.date).toLocaleDateString('ar-EG') }}
          </template>
        </Column>
        <Column field="card_uid" :header="t('card.uid')" class="text-mono">
          <template #body="{ data }">
            {{ data.card_uid || '—' }}
          </template>
        </Column>
        <Column field="type" :header="t('transaction.type')">
          <template #body="{ data }">
            <Tag :severity="data.type === 'ADD' ? 'success' : data.type === 'DEDUCT' ? 'warning' : 'info'">
              {{ t(`transaction.types.${data.type?.toLowerCase() || 'add'}`) }}
            </Tag>
          </template>
        </Column>
        <Column field="amount" :header="t('transaction.amount')">
          <template #body="{ data }">
            <span :class="['amount', data.type === 'DEDUCT' ? 'deduct' : 'add']">
              {{ data.type === 'DEDUCT' ? '-' : '+' }}{{ formatAmount(data.amount) }} ج.م
            </span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.dashboard {
  display: flex;
  flex-direction: column;
  gap: $space-6;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $space-4;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
}

.recent-section {
  background: $color-bg-surface;
  border-radius: $radius-lg;
  padding: $space-5;
  border: 1px solid $color-border;
}

.section-title {
  font-size: $text-lg;
  font-weight: 700;
  margin-bottom: $space-4;
  color: $color-text-primary;
}

.empty {
  text-align: center;
  padding: $space-6;
  color: $color-text-muted;
}

.amount {
  font-weight: 600;

  &.add { color: $color-success; }
  &.deduct { color: $color-danger; }
}
</style>
