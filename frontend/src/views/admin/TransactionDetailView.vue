<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'
import PageHeader from '@/components/layout/PageHeader.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(true)
const transaction = ref<any>(null)

async function loadTransaction() {
  loading.value = true
  try {
    const res = await api.get(`/api/v1/transactions/${route.params.id}`)
    transaction.value = res.data
  } catch { /* */ } finally {
    loading.value = false
  }
}

onMounted(loadTransaction)
</script>

<template>
  <div>
    <PageHeader :title="t('transaction.single')" :breadcrumb="[t('transaction.title')]">
      <template #actions>
        <Button :label="t('actions.back')" icon="pi pi-arrow-right" severity="secondary" outlined @click="router.push('/admin/transactions')" />
      </template>
    </PageHeader>

    <div v-if="loading" class="loading"><i class="pi pi-spinner pi-spin" style="font-size: 2rem" /></div>

    <div v-else-if="transaction" class="detail-card">
      <div class="detail-row">
        <span class="label">{{ t('transaction.id') }}:</span>
        <span class="value text-mono">{{ transaction.id }}</span>
      </div>
      <div class="detail-row">
        <span class="label">{{ t('transaction.date') }}:</span>
        <span class="value">{{ new Date(transaction.created_at).toLocaleString('ar-EG') }}</span>
      </div>
      <div class="detail-row">
        <span class="label">{{ t('card.uid') }}:</span>
        <span class="value text-mono">{{ transaction.card_uid }}</span>
      </div>
      <div class="detail-row">
        <span class="label">{{ t('transaction.type') }}:</span>
        <Tag severity="info">{{ t(`transaction.types.${transaction.type?.toLowerCase()}`) }}</Tag>
      </div>
      <div class="detail-row">
        <span class="label">{{ t('transaction.amount') }}:</span>
        <span class="value amount-display">{{ transaction.amount }} ج.م</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.loading { display: flex; justify-content: center; padding: $space-7; color: $color-text-muted; }

.detail-card {
  background: $color-bg-surface;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: $space-5;
}

.detail-row {
  display: flex;
  align-items: center;
  padding: $space-3 0;
  border-bottom: 1px solid $color-border;

  &:last-child { border-bottom: none; }

  .label { width: 140px; font-weight: 600; color: $color-text-secondary; }
  .value { color: $color-text-primary; }
}

.amount-display { font-size: $text-lg; font-weight: 700; }

.text-mono { font-family: $font-mono; }
</style>
