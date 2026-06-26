<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()
const router = useRouter()

const loading = ref(true)
const cards = ref<any[]>([])
const searchQuery = ref('')
const statusFilter = ref<string | null>(null)

const filteredCards = computed(() => {
  let result = cards.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (c) =>
        c.uid?.toLowerCase().includes(q) ||
        c.customer_name?.toLowerCase().includes(q)
    )
  }
  if (statusFilter.value) {
    result = result.filter((c) => c.status === statusFilter.value)
  }
  return result
})

async function loadCards() {
  loading.value = true
  try {
    const res = await api.get('/api/v1/cards/', {
      params: { status: statusFilter.value || undefined },
    })
    cards.value = res.data
  } catch {
    cards.value = []
  } finally {
    loading.value = false
  }
}

const statusSeverity: Record<string, string> = {
  ACTIVE: 'success',
  INACTIVE: 'secondary',
  LOST: 'danger',
  STOLEN: 'danger',
  DAMAGED: 'warning',
}

const typeSeverity: Record<string, string> = {
  REGULAR: 'info',
  VIP: 'warning',
  STAFF: 'secondary',
  TEST: 'secondary',
}

function formatBalance(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadCards)
</script>

<template>
  <div class="cards-view">
    <PageHeader :title="t('card.title')">
      <template #actions>
        <Button
          :label="t('actions.search')"
          icon="pi pi-search"
          severity="secondary"
          outlined
          @click="loadCards"
        />
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="filters">
      <InputText
        v-model="searchQuery"
        :placeholder="t('card.search')"
        class="search-input"
      />
      <Select
        v-model="statusFilter"
        :options="[
          { label: t('common.all'), value: null },
          { label: t('card.statuses.active'), value: 'ACTIVE' },
          { label: t('card.statuses.inactive'), value: 'INACTIVE' },
          { label: t('card.statuses.lost'), value: 'LOST' },
          { label: t('card.statuses.stolen'), value: 'STOLEN' },
          { label: t('card.statuses.damaged'), value: 'DAMAGED' },
        ]"
        option-label="label"
        option-value="value"
        :placeholder="t('card.status')"
        class="status-select"
        show-clear
        @change="loadCards"
      />
    </div>

    <!-- Table -->
    <div class="table-container">
      <DataTable
        :value="filteredCards"
        :loading="loading"
        striped-rows
        paginator
        :rows="20"
        :rows-per-page-options="[10, 20, 50]"
        :empty-message="t('card.noCards')"
        @row-click="(e: any) => router.push(`/admin/cards/${e.data.uid}`)"
        row-hover
      >
        <Column field="uid" :header="t('card.uid')" class="uid-col" />
        <Column field="customer_name" :header="t('card.customer')">
          <template #body="{ data }">
            {{ data.customer_name || '—' }}
          </template>
        </Column>
        <Column field="type" :header="t('card.type')">
          <template #body="{ data }">
            <Tag :severity="typeSeverity[data.type] || 'info'">
              {{ t(`card.types.${data.type?.toLowerCase() || 'regular'}`) }}
            </Tag>
          </template>
        </Column>
        <Column field="balance" :header="t('card.balance')">
          <template #body="{ data }">
            <span class="balance" :class="{ zero: data.balance <= 0 }">
              {{ formatBalance(data.balance) }} ج.م
            </span>
          </template>
        </Column>
        <Column field="status" :header="t('card.status')">
          <template #body="{ data }">
            <Tag :severity="statusSeverity[data.status] || 'secondary'">
              {{ t(`card.statuses.${data.status?.toLowerCase() || 'inactive'}`) }}
            </Tag>
          </template>
        </Column>
        <Column :header="t('actions.view')">
          <template #body>
            <i class="pi pi-chevron-left view-icon" />
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.cards-view {
  display: flex;
  flex-direction: column;
  gap: $space-4;
}

.filters {
  display: flex;
  gap: $space-3;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
}

.status-select {
  width: 160px;
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

.balance {
  font-weight: 600;
  color: $color-success;

  &.zero {
    color: $color-text-muted;
  }
}

.view-icon {
  color: $color-text-muted;
  font-size: $text-sm;
}
</style>
