import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'sindbad-locale'

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<string>('ar')

  const isArabic = computed(() => locale.value === 'ar')
  const direction = computed(() => (isArabic.value ? 'rtl' : 'ltr'))
  const fontClass = computed(() => (isArabic.value ? 'font-arabic' : 'font-latin'))

  function init() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'ar' || saved === 'en') {
      locale.value = saved
    }
    applyLocale()
  }

  function setLocale(lang: 'ar' | 'en') {
    locale.value = lang
    localStorage.setItem(STORAGE_KEY, lang)
    applyLocale()
  }

  function toggle() {
    setLocale(isArabic.value ? 'en' : 'ar')
  }

  function applyLocale() {
    document.documentElement.dir = direction.value
    document.documentElement.lang = locale.value
  }

  return { locale, isArabic, direction, fontClass, init, setLocale, toggle }
})
