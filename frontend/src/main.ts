import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { createI18n } from 'vue-i18n'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'

import App from './App.vue'
import router from './router'
import './assets/styles/global.scss'
import './assets/styles/theme.scss'
import './assets/styles/rtl.scss'

// --- i18n ---
import ar from '../public/locales/ar.json'
import en from '../public/locales/en.json'

const i18n = createI18n({
  legacy: false,
  locale: 'ar',
  fallbackLocale: 'en',
  messages: { ar, en },
})

// --- PrimeVue theme ---
const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.app-dark',
    },
  },
  ripple: true,
})
app.use(ToastService)
app.use(ConfirmationService)

app.mount('#app')
