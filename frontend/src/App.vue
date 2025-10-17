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

/* 修复暗色主题UI组件亮度问题 */

/* 1. 禁用按钮样式 - 系统设置通知渠道优先级按钮 */
html.dark .el-button.is-disabled,
html.dark .el-button.is-disabled:hover,
html.dark .el-button.is-disabled:focus {
  background-color: var(--input-bg);
  border-color: var(--border-color);
  color: var(--text-tertiary);
}

/* 2. 下拉菜单输入框 - 降低亮度 */
html.dark .el-select .el-input__wrapper {
  background-color: var(--input-bg) !important;
  box-shadow: 0 0 0 1px var(--input-border) inset !important;
}

html.dark .el-select .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--border-color) inset !important;
}

html.dark .el-select .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

html.dark .el-select-dropdown__item.hover,
html.dark .el-select-dropdown__item:hover {
  background-color: rgba(64, 158, 255, 0.15) !important;
}

/* 3. 切换按钮(Switch)的圆点和背景 - 降低亮度 */
html.dark .el-switch__core {
  background-color: var(--input-bg);
  border: 1px solid var(--border-color);
}

html.dark .el-switch__core .el-switch__action {
  background-color: #d0d0d0;
}

html.dark .el-switch.is-checked .el-switch__core {
  background-color: var(--el-color-primary);
  border-color: var(--el-color-primary);
}

html.dark .el-switch.is-checked .el-switch__core .el-switch__action {
  background-color: #ffffff;
}

/* 4. 所有输入框边框 - 降低对比度 */
html.dark .el-input__wrapper {
  background-color: var(--input-bg);
  box-shadow: 0 0 0 1px var(--input-border) inset;
}

html.dark .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

html.dark .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

/* 5. 表格边框 - 降低亮度 */
html.dark .el-table {
  --el-table-border-color: var(--border-color);
}

html.dark .el-table th,
html.dark .el-table td {
  border-color: var(--border-color);
}

html.dark .el-table--border th,
html.dark .el-table--border td {
  border-color: var(--border-color);
}

html.dark .el-table--border .el-table__inner-wrapper::after,
html.dark .el-table--border::before,
html.dark .el-table--border::after {
  background-color: var(--border-color);
}

/* 6. 描述列表(Descriptions)边框和字体 - 降低亮度 */
html.dark .el-descriptions {
  --el-descriptions-item-bordered-label-background: var(--input-bg);
  background-color: var(--card-bg);
}

html.dark .el-descriptions__label,
html.dark .el-descriptions__content {
  border-color: var(--border-color);
  color: var(--text-primary) !important;
}

html.dark .el-descriptions__label {
  background-color: var(--input-bg);
}

html.dark .el-descriptions--bordered .el-descriptions__cell {
  border-color: var(--border-color);
}

html.dark .el-descriptions__cell {
  background-color: transparent !important;
}

/* 7. 进度条空白部分区分度增强 - 使用半透明白色提供对比度但不刺眼 */
html.dark .el-progress-bar__outer {
  background-color: rgba(255, 255, 255, 0.08) !important;
}

html.dark .el-progress__text {
  color: var(--text-primary);
}

/* 8. 禁用/只读Input输入框两端亮色区域修复 */
html.dark .el-input.is-disabled .el-input__wrapper,
html.dark .el-input__wrapper.is-disabled {
  background-color: var(--input-bg) !important;
  box-shadow: 0 0 0 1px var(--input-border) inset !important;
}

/* 9. 下拉菜单收起后显示值区域修复 */
html.dark .el-select .el-input.is-focus .el-input__wrapper {
  background-color: var(--input-bg) !important;
}

html.dark .el-select .el-input__inner {
  color: var(--text-primary);
}

/* 下拉菜单项hover效果优化 */
html.dark .el-dropdown-menu__item:hover {
  background-color: rgba(64, 158, 255, 0.15) !important;
}

/* 10. 统计卡片和描述列表背景修复 */
html.dark .el-statistic {
  background-color: transparent;
}

html.dark .el-descriptions__body {
  background-color: var(--card-bg);
}

/* 其他Element Plus组件暗色优化 */

/* InputNumber加减按钮 */
html.dark .el-input-number .el-input-number__decrease,
html.dark .el-input-number .el-input-number__increase {
  background-color: var(--input-bg);
  color: var(--text-secondary);
  border-color: var(--border-color);
}

html.dark .el-input-number .el-input-number__decrease:hover,
html.dark .el-input-number .el-input-number__increase:hover {
  color: var(--el-color-primary);
}

/* Textarea */
html.dark .el-textarea__inner {
  background-color: var(--input-bg);
  color: var(--text-primary);
  border-color: var(--input-border);
}

html.dark .el-textarea__inner:hover {
  border-color: var(--border-color);
}

html.dark .el-textarea__inner:focus {
  border-color: var(--el-color-primary);
}

/* TimePicker和DatePicker */
html.dark .el-time-panel,
html.dark .el-picker-panel {
  background-color: var(--card-bg);
  border-color: var(--border-color);
}

html.dark .el-time-panel__content,
html.dark .el-picker-panel__body {
  color: var(--text-primary);
}

/* Checkbox */
html.dark .el-checkbox__inner {
  background-color: var(--input-bg);
  border-color: var(--border-color);
}

html.dark .el-checkbox__input.is-checked .el-checkbox__inner {
  background-color: var(--el-color-primary);
  border-color: var(--el-color-primary);
}

/* Tag */
html.dark .el-tag {
  border-color: var(--border-color);
}

/* Tag - Light variant 修复 */
html.dark .el-tag--light.el-tag--primary {
  background-color: rgba(64, 158, 255, 0.15) !important;
  border-color: rgba(64, 158, 255, 0.3) !important;
  color: #409eff !important;
}

html.dark .el-tag--light.el-tag--success {
  background-color: rgba(103, 194, 58, 0.15) !important;
  border-color: rgba(103, 194, 58, 0.3) !important;
  color: #67c23a !important;
}

html.dark .el-tag--light.el-tag--warning {
  background-color: rgba(230, 162, 60, 0.15) !important;
  border-color: rgba(230, 162, 60, 0.3) !important;
  color: #e6a23c !important;
}

html.dark .el-tag--light.el-tag--danger {
  background-color: rgba(245, 108, 108, 0.15) !important;
  border-color: rgba(245, 108, 108, 0.3) !important;
  color: #f56c6c !important;
}

html.dark .el-tag--light.el-tag--info {
  background-color: rgba(144, 147, 153, 0.15) !important;
  border-color: rgba(144, 147, 153, 0.3) !important;
  color: #909399 !important;
}

/* Select - 修复下拉菜单wrapper背景 */
html.dark .el-select__wrapper {
  background-color: var(--input-bg) !important;
  box-shadow: 0 0 0 1px var(--input-border) inset !important;
}

/* Select dropdown - 修复已选中项背景（非hover状态） */
html.dark .el-select-dropdown__item.is-selected {
  background-color: rgba(64, 158, 255, 0.1) !important;
  color: var(--el-color-primary);
}

html.dark .el-select-dropdown__item.is-selected.is-hovering {
  background-color: rgba(64, 158, 255, 0.15) !important;
}

/* Dialog */
html.dark .el-dialog {
  background-color: var(--card-bg);
  border: 1px solid var(--border-color);
}

html.dark .el-dialog__header {
  border-bottom: 1px solid var(--border-color);
}

html.dark .el-dialog__title {
  color: var(--text-primary);
}

html.dark .el-dialog__body {
  color: var(--text-primary);
}

/* Form表单 */
html.dark .el-form-item__label {
  color: var(--text-primary);
}

/* Divider */
html.dark .el-divider {
  border-color: var(--border-color);
}

html.dark .el-divider__text {
  background-color: var(--card-bg);
  color: var(--text-primary);
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
