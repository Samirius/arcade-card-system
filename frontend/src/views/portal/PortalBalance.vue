<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/config/api'

// FIELD NORMALIZATION REMOVED (see frontend/FRONTEND_CHANGES.md item 2):
// reads `card.card_uid` / `card.card_type` directly instead of the
// previously auto-mapped `uid` / `type`.
const { t } = useI18n()
const loading = ref(true)
const card = ref<any>(null)

async function loadBalance() {
  loading.value = true
  try {
    const res = await api.get('/api/v1/cards/me')
    card.value = res.data
  } catch { card.value = null } finally { loading.value = false }
}

function formatAmount(amount: number) {
  return new Intl.NumberFormat('ar-EG', { minimumFractionDigits: 0 }).format(amount)
}

onMounted(loadBalance)
</script>

<template>
  <div class="portal-balance">
    <div v-if="loading" class="loading"><i class="pi pi-spinner pi-spin" /></div>

    <div v-else-if="card" class="balance-card">
      <div class="balance-label">{{ t('portal.balance') }}</div>
      <div class="balance-amount">{{ formatAmount(card.balance) }}</div>
      <div class="balance-currency">ج.م</div>

      <div class="card-info">
        <span class="card-uid text-mono">{{ card.card_uid }}</span>
        <Tag severity="warning" v-if="card.card_type === 'VIP'">VIP</Tag>
      </div>

      <Button
        :label="t('portal.refresh')"
        icon="pi pi-refresh"
        severity="secondary"
        text
        @click="loadBalance"
        class="refresh-btn"
      />
    </div>

    <div v-else class="no-card">
      <i class="pi pi-exclamation-triangle" style="font-size: 2rem" />
      <p>{{ t('common.noData') }}</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/tokens.scss' as *;

.portal-balance { display: flex; flex-direction: column; gap: $space-4; align-items: center; }
.loading, .no-card { padding: $space-7; text-align: center; color: $color-text-muted; }

.balance-card {
  background: linear-gradient(135deg, $color-brand-primary 0%, $color-brand-primary-dark 100%);
  color: white;
  border-radius: $radius-lg;
  padding: $space-6;
  width: 100%;
  text-align: center;
}

.balance-label { font-size: $text-base; opacity: 0.8; margin-bottom: $space-2; }
.balance-amount { font-size: 3.5rem; font-weight: 800; line-height: 1; }
.balance-currency { font-size: $text-lg; opacity: 0.8; margin-top: $space-1; }

.card-info {
  display: flex; align-items: center; justify-content: center; gap: $space-2;
  margin-top: $space-4;
}

.card-uid { font-size: $text-sm; opacity: 0.7; }

.refresh-btn { color: white; margin-top: $space-3; }

.text-mono { font-family: $font-mono; }
</style>
