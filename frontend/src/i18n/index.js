import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.json'
import enUS from './locales/en-US.json'

// 创建i18n实例
const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: localStorage.getItem('locale') || 'zh-CN', // 默认语言
  fallbackLocale: 'zh-CN', // 回退语言
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  },
  globalInjection: true // 全局注入 $t 函数
})

export default i18n
