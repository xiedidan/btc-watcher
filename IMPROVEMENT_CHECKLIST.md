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
- [ ] Router meta titles - 需要i18n支持
- [ ] 404/错误页面 - 需检查是否存在
- [ ] 消息提示/确认对话框 - 已统一使用i18n ✅

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

### 2.3 其他暗色主题优化
- [ ] 检查卡片阴影效果
- [ ] 检查按钮hover状态
- [ ] 检查标签(Tag)组件颜色
- [ ] 检查对话框(Dialog)背景色
- [ ] 检查消息提示(Message)颜色

---

## 三、功能改进 🚀

### 3.1 代理管理功能
**问题**: Proxy API无法访问，缺少priority字段
**位置**: `backend/models/proxy.py`
**状态**: 🔄 待修复
**修复方案**:
- 添加priority字段到Proxy模型
- 创建数据库迁移
- 更新API查询以支持优先级排序

### 3.2 通知系统
- [x] NotificationHistory模型字段冲突 (metadata → extra_data) ✅
- [ ] 通知渠道配置功能完善
- [ ] 通知测试功能实现
- [ ] 频率限制逻辑实现

### 3.3 WebSocket连接
- [ ] 重连逻辑优化
- [ ] 心跳机制完善
- [ ] 主题订阅管理

---

## 四、性能优化 ⚡

### 4.1 前端性能
- [ ] 图表数据更新优化 (减少重绘)
- [ ] 大列表虚拟滚动 (如信号列表)
- [ ] 路由懒加载检查
- [ ] 静态资源压缩

### 4.2 后端性能
- [ ] API响应时间优化
- [ ] 数据库查询优化
- [ ] 缓存策略实现

---

## 五、代码质量 📝

### 5.1 代码规范
- [ ] ESLint规则统一
- [ ] 组件命名规范检查
- [ ] 注释完善

### 5.2 测试覆盖
- [ ] 单元测试补充
- [ ] E2E测试场景
- [ ] API测试完善

---

## 六、用户体验 ✨

### 6.1 响应式设计
- [ ] 移动端适配检查
- [ ] 平板端布局优化
- [ ] 小屏幕显示优化

### 6.2 交互优化
- [ ] 加载状态优化
- [ ] 错误提示友好化
- [ ] 操作反馈及时性

### 6.3 可访问性
- [ ] 键盘导航支持
- [ ] 屏幕阅读器支持
- [ ] 颜色对比度检查

---

## 七、文档完善 📚

### 7.1 用户文档
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

---

**注**: 此清单会持续更新，每完成一项会标记 ✅，新发现的问题会及时添加。
