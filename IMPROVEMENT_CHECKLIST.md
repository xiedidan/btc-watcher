# BTC Watcher 改进需求清单

## 文档信息
- 创建日期: 2025-10-17
- 最后更新: 2025-10-17
- 状态: 进行中

## 一、国际化(i18n)支持 🌐

### 1.1 已完成 ✅
- [x] Dashboard.vue - 完全支持中英文切换
- [x] Monitoring.vue - 完全支持中英文切换
- [x] Login.vue - 完全支持中英文切换
- [x] MainLayout.vue - 完全支持中英文切换
- [x] 翻译文件基础设施 (zh-CN.json, en-US.json)
- [x] Settings页面翻译键值准备 (200+个键值)
- [x] Settings.vue - 完全支持中英文切换 (200+ t()调用)

### 1.2 待完成 ⏳

#### 1.2.1 Settings.vue (系统设置页面)
**优先级: P0 (紧急)** ✅ 已完成
- [x] 页面标题和保存按钮
- [x] 通知渠道标签页
  - [x] 渠道配置表格 (优先级、渠道类型、渠道名称等)
  - [x] 频率限制配置表单
  - [x] 时间规则配置表单
  - [x] 渠道配置对话框 (SMS、飞书、微信、Email、Telegram)
- [x] 通知设置标签页
- [x] WebSocket设置标签页
- [x] 显示设置标签页
- [x] 账户设置标签页
- [x] 高级设置标签页
- [x] 关于标签页
**翻译键值**: 已完成集成 (200+ keys)

#### 1.2.2 Strategies.vue (策略管理页面)
**优先级: P0 (紧急)** ✅ 已完成
- [x] 页面标题和操作按钮
- [x] 策略列表表格
- [x] 创建/编辑策略对话框
- [x] 状态标签和操作按钮
- [x] 草稿管理功能
- [x] 文件上传提示和验证
- [x] 健康分数显示
- [x] 策略详情对话框
**翻译键值**: 已完成集成 (100+ keys)

#### 1.2.3 Signals.vue (信号列表页面)
**优先级: P1 (重要)** ✅ 已完成
- [x] 页面标题和筛选器
- [x] 信号列表表格
- [x] 信号详情对话框
- [x] 信号类型和强度标签
**翻译键值**: 已完成集成 (56 keys)

#### 1.2.4 Proxies.vue (代理管理页面)
**优先级: P1 (重要)** ✅ 已完成
- [x] 页面标题和操作按钮
- [x] 代理列表表格
- [x] 创建/编辑代理对话框
- [x] 测试连接功能
**翻译键值**: 已完成集成 (71 keys)

#### 1.2.5 其他页面检查
- [x] Drafts.vue (草稿管理) - 已完成 ✅ (86 keys)
- [x] Router meta titles - 已完成 ✅
- [x] MainLayout breadcrumb - 已完成 ✅
- [ ] 404/错误页面 - 不存在
- [ ] 消息提示/确认对话框 - 已统一使用i18n ✅

#### 1.2.6 Router和MainLayout i18n遗漏 🆕 ✅
**问题**:
1. router/index.js中的meta.title使用硬编码中文
2. MainLayout.vue的breadcrumb直接显示meta.title，未使用$t()翻译
**位置**:
- `frontend/src/router/index.js`
- `frontend/src/layouts/MainLayout.vue` 第62-64行
**状态**: ✅ 已修复
**修复方案**:
1. 将router meta.title改为i18n key (如 'nav.dashboard')
2. MainLayout中使用 `{{ $t($route.meta.title) }}` 翻译

### 1.3 翻译质量检查
- [ ] 检查所有翻译键值的英文表达是否准确自然
- [ ] 检查中文翻译是否专业规范
- [ ] 统一术语翻译 (如Strategy/策略, Signal/信号等)
- [ ] 检查变量插值格式 ({count}, {name}等)

---

## 二、暗色主题优化 🌙

### 2.1 字体颜色问题 ✅ (部分)

#### 2.1.1 系统监控页面 - 系统详细信息表
**问题**: 暗色主题下字体颜色过深，难以阅读
**位置**: `frontend/src/views/Monitoring.vue`
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-descriptions {
  background-color: var(--card-bg);
}

html.dark .el-descriptions__label,
html.dark .el-descriptions__content {
  color: var(--text-primary) !important;
}
```

#### 2.1.2 其他可能的字体颜色问题
- [ ] 检查Dashboard中的图表文字颜色
- [ ] 检查Settings中的表单标签颜色
- [ ] 检查所有表格内容的可读性

### 2.2 UI组件亮度问题

#### 2.2.1 系统设置 - 通知渠道 - 优先级按钮
**问题**: 无效状态的按钮(最上和最下)在暗色主题下太亮
**位置**: `frontend/src/views/Settings.vue`
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-button.is-disabled {
  background-color: var(--input-bg);
  border-color: var(--border-color);
  color: var(--text-tertiary);
}
```

#### 2.2.2 所有下拉菜单的输入框部分
**问题**: 下拉菜单输入框在暗色主题下背景太亮
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-select .el-input__wrapper {
  background-color: var(--input-bg);
  box-shadow: 0 0 0 1px var(--input-border) inset;
}

html.dark .el-select .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--border-color) inset;
}
```

#### 2.2.3 所有切换按钮(Switch)的圆点
**问题**: Switch按钮的圆点在暗色主题下太亮
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-switch__core {
  background-color: var(--input-bg);
  border-color: var(--border-color);
}

html.dark .el-switch__core .el-switch__action {
  background-color: #ffffff;
}

html.dark .el-switch.is-checked .el-switch__core {
  background-color: var(--el-color-primary);
}
```

#### 2.2.4 所有输入框的两端
**问题**: 输入框边框在暗色主题下太亮
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-input__wrapper {
  background-color: var(--input-bg);
  box-shadow: 0 0 0 1px var(--input-border) inset;
}

html.dark .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

html.dark .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}
```

#### 2.2.5 系统详细信息和系统监控的表格边框
**问题**: 表格边框在暗色主题下太亮，对比度过高
**位置**: `frontend/src/views/Monitoring.vue` 和全局样式
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-table {
  --el-table-border-color: var(--border-color);
}

html.dark .el-table th,
html.dark .el-table td {
  border-color: var(--border-color);
}

html.dark .el-descriptions {
  --el-descriptions-item-bordered-label-background: var(--input-bg);
}

html.dark .el-descriptions__label,
html.dark .el-descriptions__content {
  border-color: var(--border-color);
}
```

#### 2.2.6 系统健康状态的三个使用率进度条(空白部分)
**问题**: 进度条未填充部分在暗色主题下太亮
**位置**: `frontend/src/views/Monitoring.vue`
**状态**: 🔄 待修复
**修复方案**:
```css
html.dark .el-progress-bar__outer {
  background-color: var(--input-bg);
}

html.dark .el-progress__text {
  color: var(--text-primary);
}
```

#### 2.2.7 锁定的Input输入框两端亮色区域 🆕 ✅
**问题**: 禁用/只读状态的Input输入框两端（可能是padding区域）有小块亮色区域
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-input.is-disabled .el-input__wrapper,
html.dark .el-input__wrapper.is-disabled {
  background-color: var(--input-bg) !important;
  box-shadow: 0 0 0 1px var(--input-border) inset !important;
}
```

#### 2.2.8 下拉菜单收起后显示值部分亮色 🆕 ✅
**问题**: el-select下拉菜单收起后，显示选中值的input区域背景是亮色的
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-select .el-input.is-focus .el-input__wrapper {
  background-color: var(--input-bg) !important;
}

html.dark .el-select .el-input__inner {
  color: var(--text-primary);
}
```

#### 2.2.9 系统健康状态进度条空白部分区分度不够 🆕 ✅
**问题**: 进度条未填充部分与背景色区分度不够，但不能变成亮色
**位置**: `frontend/src/views/Monitoring.vue` 或全局样式
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-progress-bar__outer {
  background-color: rgba(255, 255, 255, 0.08) !important;
}
```

#### 2.2.10 统计卡片（今日信号、最后更新）背景太亮 🆕 ✅
**问题**: Dashboard中的统计框（如今日信号、最后更新）背景色太亮
**位置**: `frontend/src/views/Dashboard.vue` 或全局样式
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-statistic {
  background-color: transparent;
}

html.dark .el-descriptions__body {
  background-color: var(--card-bg);
}
```

#### 2.2.11 下拉菜单收起状态显示值背景仍然亮色 🆕 ✅
**问题**: el-select下拉菜单收起后，显示选中值的区域背景依然是亮色的（之前修复未生效）
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-select .el-input__wrapper {
  background-color: var(--input-bg) !important;
  box-shadow: 0 0 0 1px var(--input-border) inset !important;
}
```

#### 2.2.12 下拉菜单hover选中项背景变亮 🆕 ✅
**问题**: 鼠标hover下拉菜单项时，背景变成亮色
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-select-dropdown__item.hover,
html.dark .el-select-dropdown__item:hover {
  background-color: rgba(64, 158, 255, 0.15) !important;
}
```

#### 2.2.13 系统监控-系统详细信息-最后更新背景太亮 🆕 ✅
**问题**: Monitoring页面的"最后更新"描述框背景色太亮
**位置**: `frontend/src/views/Monitoring.vue` 或全局样式
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-descriptions__cell {
  background-color: transparent !important;
}
```

#### 2.2.14 信号列表-今日信号统计卡片背景太亮 🆕 ✅
**问题**: Signals页面顶部的"今日信号"统计卡片背景太亮
**位置**: `frontend/src/views/Signals.vue` 或全局样式
**状态**: ✅ 已修复
**修复方案**: 与2.2.10相同，检查是否已生效

#### 2.2.15 仪表盘-信号分布图例文字太暗 🆕 ✅
**问题**: Dashboard的信号分布图表图例文字在暗色主题下太暗，难以阅读
**位置**: `frontend/src/views/Dashboard.vue` 中的ECharts配置
**状态**: ✅ 已修复
**修复方案**: 在图表option中设置legend文字颜色，使用computed属性动态切换

#### 2.2.16 el-tag--light标签背景过亮 (监控页面Last Update) 🆕 ✅
**问题**: 监控页面的 "Last Update: 2025/10/17 10:47:52" 标签背景过亮
**HTML元素**: `<span class="el-tag el-tag--primary el-tag--small el-tag--light">`
**位置**: `frontend/src/views/Monitoring.vue` 或全局样式
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-tag--light.el-tag--primary {
  background-color: rgba(64, 158, 255, 0.15) !important;
  border-color: rgba(64, 158, 255, 0.3) !important;
  color: #409eff !important;
}
```

#### 2.2.17 el-tag--light标签背景过亮 (信号页面今日信号) 🆕 ✅
**问题**: 信号页面的 "今日信号: 0" 标签背景过亮
**HTML元素**: `<span class="el-tag el-tag--primary el-tag--light">`
**位置**: `frontend/src/views/Signals.vue` 或全局样式
**状态**: ✅ 已修复
**修复方案**: 与2.2.16相同，同时添加了所有颜色变体的支持

#### 2.2.18 下拉菜单已选中项背景过亮 (未hover时) 🆕 ✅
**问题**: 下拉菜单中已选中的项，在未hover时背景过亮
**HTML元素**: `<li class="el-select-dropdown__item is-selected">`
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-select-dropdown__item.is-selected {
  background-color: rgba(64, 158, 255, 0.1) !important;
}
```

#### 2.2.19 下拉菜单wrapper背景过亮 🆕 ✅
**问题**: 下拉菜单本身（未展开状态）的背景过亮
**HTML元素**: `<div class="el-select__wrapper">`
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-select__wrapper {
  background-color: var(--input-bg) !important;
  box-shadow: 0 0 0 1px var(--input-border) inset !important;
}
```

#### 2.2.20 下拉菜单项普通状态背景过亮 (未hover未选中) 🆕 ✅
**问题**: 下拉菜单项在非hover、非选中的普通状态下背景过亮
**HTML元素**: `<li class="el-select-dropdown__item">` (无is-selected, 无is-hovering)
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**分析**: 之前只修复了hover和selected状态，遗漏了普通状态的背景色设置，导致继承了Element Plus的默认亮色背景
**修复方案**:
```css
html.dark .el-select-dropdown__item {
  background-color: transparent;
  color: var(--text-primary);
}
```

#### 2.2.21 el-alert is-light 组件背景过亮 🆕 ✅
**问题**: Alert提示框（light变体）在暗色主题下背景过亮
**HTML元素**: `<div class="el-alert el-alert--info is-light">`
**示例**: 策略管理页面的"0个修改中"提示框
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-alert.is-light.el-alert--info {
  background-color: rgba(64, 158, 255, 0.15) !important;
  border-color: rgba(64, 158, 255, 0.3) !important;
}
```
**额外收获**: 同时修复了所有alert颜色变体(info/success/warning/error)

#### 2.2.22 el-button is-text hover时背景过亮 🆕 ✅
**问题**: 文本按钮hover时背景过亮（顶部用户下拉菜单）
**HTML元素**: `<button class="el-button is-text">`
**示例**: MainLayout顶部栏的用户下拉菜单按钮
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-button.is-text:hover {
  background-color: rgba(64, 158, 255, 0.1) !important;
}
```

#### 2.2.23 el-checkbox__inner 复选框过亮 🆕 ✅
**问题**: Checkbox复选框在暗色主题下过亮
**HTML元素**: `<span class="el-checkbox__inner">`
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**分析**: 需要使用!important强制覆盖Element Plus的默认样式
**修复方案**:
```css
html.dark .el-checkbox__inner {
  background-color: var(--input-bg) !important;
  border-color: var(--border-color) !important;
}
```

#### 2.2.24 el-popper__arrow dropdown箭头过亮 🆕 ✅
**问题**: Dropdown下拉菜单的小三角箭头在暗色主题下过亮
**HTML元素**: `<span class="el-popper__arrow">`
**位置**: 全局样式 `frontend/src/App.vue`
**状态**: ✅ 已修复
**修复方案**:
```css
html.dark .el-popper__arrow::before {
  background: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
}
```

### 2.3 其他暗色主题优化
- [ ] 检查卡片阴影效果
- [ ] 检查按钮hover状态
- [ ] 检查标签(Tag)组件颜色
- [ ] 检查对话框(Dialog)背景色
- [ ] 检查消息提示(Message)颜色

---

## 三、UI布局和导航优化 🎨

### 3.1 UI组件宽度问题

#### 3.1.1 策略管理-状态下拉菜单宽度过窄 🆕 ✅
**问题**: 策略管理页面的状态筛选下拉菜单宽度太窄，选项文字显示不全
**位置**: `frontend/src/views/Strategies.vue`
**状态**: ✅ 已修复
**修复方案**: 增加el-select组件的宽度
```vue
<el-select v-model="searchForm.status" style="width: 120px">
```

### 3.2 导航层级问题

#### 3.2.1 草稿管理面包屑导航层次错误 🆕 ✅
**问题**: 草稿管理是策略管理的二级页面，但面包屑显示"首页/草稿管理"，缺少"策略管理"层级
**应该显示**: 首页 / 策略管理 / 草稿管理
**当前显示**: 首页 / 草稿管理
**位置**: `frontend/src/router/index.js` 和 `frontend/src/layouts/MainLayout.vue`
**状态**: ✅ 已修复
**修复方案**: 在MainLayout中添加特殊处理逻辑，当路径是/drafts时，添加策略管理层级
```vue
<el-breadcrumb-item v-if="$route.path === '/drafts'" :to="{ path: '/strategies' }">
  {{ $t('nav.strategies') }}
</el-breadcrumb-item>
```

---

## 四、功能改进 🚀

### 4.1 代理管理功能
**问题**: Proxy API无法访问，缺少priority字段
**位置**: `backend/models/proxy.py`
**状态**: 🔄 待修复
**修复方案**:
- 添加priority字段到Proxy模型
- 创建数据库迁移
- 更新API查询以支持优先级排序

### 4.2 通知系统
- [x] NotificationHistory模型字段冲突 (metadata → extra_data) ✅
- [ ] 通知渠道配置功能完善
- [ ] 通知测试功能实现
- [ ] 频率限制逻辑实现

### 4.3 WebSocket连接
- [ ] 重连逻辑优化
- [ ] 心跳机制完善
- [ ] 主题订阅管理

---

## 五、性能优化 ⚡

### 5.1 前端性能
- [ ] 图表数据更新优化 (减少重绘)
- [ ] 大列表虚拟滚动 (如信号列表)
- [ ] 路由懒加载检查
- [ ] 静态资源压缩

### 5.2 后端性能
- [ ] API响应时间优化
- [ ] 数据库查询优化
- [ ] 缓存策略实现

---

## 六、代码质量 📝

### 6.1 代码规范
- [ ] ESLint规则统一
- [ ] 组件命名规范检查
- [ ] 注释完善

### 6.2 测试覆盖
- [ ] 单元测试补充
- [ ] E2E测试场景
- [ ] API测试完善

---

## 七、用户体验 ✨

### 7.1 响应式设计
- [ ] 移动端适配检查
- [ ] 平板端布局优化
- [ ] 小屏幕显示优化

### 7.2 交互优化
- [ ] 加载状态优化
- [ ] 错误提示友好化
- [ ] 操作反馈及时性

### 7.3 可访问性
- [ ] 键盘导航支持
- [ ] 屏幕阅读器支持
- [ ] 颜色对比度检查

---

## 八、文档完善 📚

### 8.1 用户文档
- [ ] 功能使用说明
- [ ] FAQ文档
- [ ] 视频教程

### 7.2 开发文档
- [ ] API文档完善
- [ ] 组件文档
- [ ] 部署文档

---

## 优先级总结

### P0 - 紧急 (本次迭代必须完成)
1. ✅ 修复系统详细信息表字体颜色问题
2. ✅ 修复所有暗色主题UI组件亮度问题
3. ✅ Settings.vue i18n集成
4. ✅ Strategies.vue i18n支持
5. ✅ Signals.vue i18n支持
6. ✅ Proxies.vue i18n支持

### P1 - 重要 (下次迭代优先)
1. 代理管理功能修复
2. 其他页面i18n检查
3. 翻译质量检查
4. 暗色主题全面检查

### P2 - 一般 (持续改进)
1. 性能优化
2. 代码质量提升
3. 测试覆盖
4. 文档完善

---

## 变更日志

### 2025-10-17
- 创建改进需求清单
- 识别暗色主题问题6项
- 识别i18n待完成页面4个
- 设置优先级和修复方案
- 完成Settings.vue i18n集成 (200+ keys)
- 完成Strategies.vue i18n集成 (100+ keys)
- 完成Signals.vue i18n集成 (56 keys)
- 完成Proxies.vue i18n集成 (71 keys)
- 完成Drafts.vue i18n集成 (86 keys)
- 总计添加 513+ 翻译键值 (1026+ 包含中英文)
- 新增4个暗色主题问题并全部修复:
  * 锁定Input两端亮色区域 ✅
  * 下拉菜单收起后显示值亮色 ✅
  * 进度条空白部分区分度增强 ✅
  * 统计卡片背景太亮 ✅
- 新增5个暗色主题问题并全部修复:
  * 下拉菜单收起状态显示值背景仍然亮色 ✅
  * 下拉菜单hover选中项背景变亮 ✅
  * 系统监控-系统详细信息-最后更新背景太亮 ✅
  * 信号列表-今日信号统计卡片背景太亮 ✅
  * 仪表盘-信号分布图例文字太暗 ✅
- 修复Router和MainLayout i18n遗漏:
  * Router meta.title转换为i18n keys ✅
  * MainLayout breadcrumb使用$t()翻译 ✅
- 新增4个"老大难"暗色主题问题并全部修复:
  * el-tag--light标签背景过亮(监控页面Last Update) ✅
  * el-tag--light标签背景过亮(信号页面今日信号) ✅
  * 下拉菜单已选中项背景过亮(未hover时) ✅
  * 下拉菜单wrapper背景过亮 ✅
  * 额外修复了所有tag颜色变体(success/warning/danger/info) ✅
- 修复最后一个老大难问题:
  * 下拉菜单项普通状态背景过亮(未hover未选中) ✅
  * 根本原因：遗漏了el-select-dropdown__item普通状态的背景色设置 ✅
- 持续发现并修复4个新的暗色主题问题:
  * el-alert.is-light组件背景过亮 ✅
  * el-button.is-text hover时背景过亮 ✅
  * el-checkbox__inner复选框过亮 ✅
  * el-popper__arrow dropdown箭头过亮 ✅
  * 额外修复了所有alert颜色变体(info/success/warning/error) ✅
- 修复2个UI布局和导航问题:
  * 策略管理-状态下拉菜单宽度过窄 ✅
  * 草稿管理面包屑导航层次错误 ✅

---

**注**: 此清单会持续更新，每完成一项会标记 ✅，新发现的问题会及时添加。
