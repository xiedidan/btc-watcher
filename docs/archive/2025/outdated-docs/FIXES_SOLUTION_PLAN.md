# BTC Watcher 问题修复方案

## 问题清单

1. ✅ i18n语言切换 - 已完成基础配置
2. 系统设置-通知渠道UI刷新问题
3. 暗色主题控件和Tab样式问题
4. 策略容量趋势改为信号趋势
5. 分页控件语言切换
6. 系统设置保存按钮无效
7. 代理管理后端接口未实现

## 实施优先级

### 第一批（核心功能）
1. **i18n完整实现**
   - ✅ 安装vue-i18n
   - ✅ 创建语言资源文件 (zh-CN.json, en-US.json)
   - ✅ 配置i18n实例
   - ✅ 集成到locale store
   - ✅ 更新main.js
   - ⏳ 更新App.vue使用ConfigProvider
   - ⏳ 更新Login.vue使用i18n
   - ⏳ 更新MainLayout使用i18n
   - ⏳ Element Plus分页组件locale配置

2. **代理管理后端API** (优先级最高，前端已有但后端缺失)
   - 检查backend/api/v1/proxies.py是否存在
   - 如不存在，创建完整的代理管理API
   - 注册到main.py

### 第二批（UI/UX修复）
3. **暗色主题修复**
   - 补充el-tabs样式
   - 补充表单控件暗色样式
   - 修复未选中Tab与背景对比度

4. **通知渠道UI刷新**
   - 检查Settings.vue中通知渠道加载逻辑
   - 添加nextTick确保DOM更新
   - 优化响应式数据绑定

5. **系统设置保存按钮**
   - 修复saveSettings方法
   - 连接到实际API
   - 添加保存成功/失败反馈

### 第三批（功能优化）
6. **信号趋势图表**
   - 修改Dashboard.vue
   - 更新后端API返回信号趋势数据
   - 支持按货币对/策略分组
   - 同步更新设计文档

## 快速修复脚本

由于问题较多，建议分步执行，先完成代理API（用户反馈最强烈），再完成i18n集成，最后处理UI细节。
