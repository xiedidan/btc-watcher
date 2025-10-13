import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ECharts from 'vue-echarts'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// Pinia状态管理
app.use(createPinia())

// Vue Router
app.use(router)

// Element Plus
app.use(ElementPlus)

// 注册所有Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册ECharts组件
app.component('v-chart', ECharts)

app.mount('#app')
