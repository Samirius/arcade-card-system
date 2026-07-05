import { createI18n } from 'vue-i18n'

import ar from '../public/locales/ar.json'
import en from '../public/locales/en.json'

/**
 * Shared vue-i18n instance.
 * Lives in its own module (not main.ts) so the locale store can import it
 * and keep translations in sync with the chosen language.
 */
export const i18n = createI18n({
  legacy: false,
  locale: 'ar',
  fallbackLocale: 'en',
  messages: { ar, en },
})
