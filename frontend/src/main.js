import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/theme.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ECharts from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, CandlestickChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkPointComponent
} from 'echarts/components'
import i18n from './i18n'
import zhCnElementLocale from 'element-plus/dist/locale/zh-cn.mjs'
import enElementLocale from 'element-plus/dist/locale/en.mjs'

import App from './App.vue'
import router from './router'

// 注册ECharts必需组件
use([
  CanvasRenderer,
  LineChart,
  PieChart,
  CandlestickChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkPointComponent
])

const app = createApp(App)

// Pinia状态管理
app.use(createPinia())

// Vue Router
app.use(router)

// i18n国际化
app.use(i18n)

// Element Plus with locale
// 动态选择Element Plus的locale
const getElementPlusLocale = () => {
  const locale = localStorage.getItem('locale') || 'zh-CN'
  return locale === 'en-US' ? enElementLocale : zhCnElementLocale
}

app.use(ElementPlus, {
  locale: getElementPlusLocale()
})

// 注册所有Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册ECharts组件
app.component('v-chart', ECharts)

app.mount('#app')
