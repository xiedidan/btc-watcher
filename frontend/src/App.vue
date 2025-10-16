<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useLocaleStore } from '@/stores/locale'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'

const userStore = useUserStore()
const localeStore = useLocaleStore()

// 动态获取Element Plus locale
const elementLocale = computed(() => {
  return localeStore.locale === 'en-US' ? en : zhCn
})

onMounted(() => {
  // 检查登录状态
  userStore.checkAuth()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* CSS Variables for themes */
:root {
  --bg-color: #f0f2f5;
  --card-bg: #ffffff;
  --text-primary: #303133;
  --text-secondary: #606266;
  --text-tertiary: #909399;
  --border-color: #dcdfe6;
  --input-bg: #ffffff;
  --input-border: #dcdfe6;
}

html.dark {
  --bg-color: #1a1a1a;
  --card-bg: #2a2a2a;
  --text-primary: #e0e0e0;
  --text-secondary: #b0b0b0;
  --text-tertiary: #808080;
  --border-color: #404040;
  --input-bg: #333333;
  --input-border: #505050;
}

html, body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol',
    'Noto Color Emoji';
  background-color: var(--bg-color);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
}

#app {
  height: 100%;
}

/* Dark theme for Element Plus components */
html.dark .el-card {
  background-color: var(--card-bg);
  border-color: var(--border-color);
  color: var(--text-primary);
}

html.dark .el-input__wrapper {
  background-color: var(--input-bg);
  box-shadow: 0 0 0 1px var(--input-border) inset;
}

html.dark .el-input__inner {
  background-color: var(--input-bg);
  color: var(--text-primary);
}

html.dark .el-select {
  --el-select-input-focus-border-color: #409eff;
}

html.dark .el-select .el-input__wrapper {
  background-color: var(--input-bg);
}

html.dark .el-select-dropdown {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

html.dark .el-select-dropdown__item {
  color: var(--text-primary);
}

html.dark .el-select-dropdown__item.hover,
html.dark .el-select-dropdown__item:hover {
  background-color: rgba(64, 158, 255, 0.1);
}

html.dark .el-popper {
  background-color: var(--card-bg);
  border-color: var(--border-color);
  color: var(--text-primary);
}

html.dark .el-table {
  background-color: var(--card-bg);
  color: var(--text-primary);
}

html.dark .el-table th.el-table__cell {
  background-color: #333;
  color: var(--text-primary);
}

html.dark .el-table tr {
  background-color: var(--card-bg);
}

html.dark .el-table td.el-table__cell {
  border-color: var(--border-color);
}

html.dark .el-table--enable-row-hover .el-table__body tr:hover > td {
  background-color: rgba(64, 158, 255, 0.1);
}

html.dark .el-descriptions__label {
  color: var(--text-secondary);
}

html.dark .el-descriptions__content {
  color: var(--text-primary);
}

html.dark .el-progress__text {
  color: var(--text-primary);
}

html.dark .el-input-number {
  --el-input-number-controls-bg-color: var(--input-bg);
}

html.dark .el-input-number .el-input-number__decrease,
html.dark .el-input-number .el-input-number__increase {
  background-color: var(--input-bg);
  color: var(--text-primary);
  border-color: var(--border-color);
}

html.dark .el-textarea__inner {
  background-color: var(--input-bg);
  color: var(--text-primary);
  border-color: var(--input-border);
}

html.dark .el-radio-button__inner {
  background-color: var(--input-bg);
  border-color: var(--border-color);
  color: var(--text-primary);
}

html.dark .el-radio-button__original-radio:checked + .el-radio-button__inner {
  background-color: #409eff;
  border-color: #409eff;
  color: #ffffff;
}

html.dark .el-dropdown-menu {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

html.dark .el-dropdown-menu__item {
  color: var(--text-primary);
}

html.dark .el-dropdown-menu__item:hover {
  background-color: rgba(64, 158, 255, 0.1);
}

/* 全局调整 Element Plus 组件间距 */
.el-card {
  --el-card-padding: 12px;
}

.el-card__header {
  padding: 10px 12px;
}

.el-table {
  font-size: 12px;
}

.el-table th.el-table__cell {
  padding: 8px 0;
}

.el-table td.el-table__cell {
  padding: 8px 0;
}
</style>
