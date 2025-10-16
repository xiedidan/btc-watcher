import { defineStore } from 'pinia'
import { ref } from 'vue'
import i18n from '@/i18n'

export const useLocaleStore = defineStore('locale', () => {
  // State
  const locale = ref(localStorage.getItem('locale') || 'zh-CN')

  // Actions
  function setLocale(lang) {
    locale.value = lang
    localStorage.setItem('locale', lang)
    // 更新i18n的locale
    i18n.global.locale.value = lang
  }

  // 初始化时设置i18n的locale
  i18n.global.locale.value = locale.value

  return {
    locale,
    setLocale
  }
})
