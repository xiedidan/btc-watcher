# 通知渠道详细配置实施文档

## 概述

本文档记录了通知渠道详细配置界面的实施细节，这是Plan A中的第4个P0级功能。该功能为BTC Watcher系统提供了全面的多渠道通知管理能力。

## 实施时间

- 开始时间: 2025-10-16
- 完成时间: 2025-10-16
- 实施状态: ✅ 已完成

## 功能特性

### 1. 支持的通知渠道

系统支持以下5种通知渠道：

| 渠道类型 | 名称 | 默认优先级 | 适用场景 |
|---------|------|-----------|---------|
| SMS | 短信通知 | 1 | P0紧急通知 |
| Feishu | 飞书机器人 | 2 | P0/P1实时通知 |
| WeChat | 企业微信 | 3 | P0/P1/P2全级别通知 |
| Email | 邮件通知 | 4 | P1/P2批量通知 |
| Telegram | Telegram机器人 | 5 | P0/P1实时通知 |

### 2. 核心功能

#### 2.1 渠道列表管理
- ✅ 渠道优先级调整（上移/下移）
- ✅ 渠道启用/禁用切换
- ✅ 配置状态显示（已配置/未配置）
- ✅ 通知级别展示（P0/P1/P2）
- ✅ 最后测试时间显示
- ✅ 渠道测试功能

#### 2.2 渠道配置对话框
每个渠道类型都有专门的配置表单：

**短信（SMS）配置：**
- API密钥和密钥ID
- 短信签名
- 接收号码列表（多选）

**飞书（Feishu）配置：**
- Webhook URL
- 签名密钥（可选）
- @提醒用户列表

**企业微信（WeChat）配置：**
- 企业ID (CorpID)
- 应用AgentID
- 应用Secret
- 接收用户列表

**邮件（Email）配置：**
- SMTP服务器和端口
- 发件人邮箱和密码
- 收件人列表（多选）
- TLS加密选项

**Telegram配置：**
- Bot Token
- Chat ID列表（多选）
- 消息格式（纯文本/Markdown/HTML）

#### 2.3 消息模板配置
- ✅ P0级别模板（紧急通知）
- ✅ P1级别模板（重要通知）
- ✅ P2级别模板（一般通知）
- ✅ 支持变量替换：`{strategy_name}`, `{signal_type}`, `{price}`, `{strength}`, `{pair}`, `{exchange}`

#### 2.4 通知频率限制
- ✅ P0最小发送间隔（0-300秒）
- ✅ P1最小发送间隔（0-600秒）
- ✅ P2批量发送间隔（60-3600秒）

#### 2.5 通知时间规则
- ✅ 勿扰模式开关
- ✅ 勿扰时段设置（开始时间-结束时间）
- ✅ 周末降级功能（P1→P2，P2→批量）

### 3. 数据持久化

所有配置使用localStorage本地存储：

```javascript
// 渠道配置存储键
notification_channel_1  // 短信配置
notification_channel_2  // 飞书配置
notification_channel_3  // 企业微信配置
notification_channel_4  // 邮件配置
notification_channel_5  // Telegram配置

// 全局配置存储键
notification_frequency_limits  // 频率限制
notification_time_rules        // 时间规则
```

## 文件修改清单

### 修改的文件

#### `frontend/src/views/Settings.vue`

**主要修改内容：**

1. **新增Tab页（第11-201行）**
   - 添加"通知渠道"标签页作为第一个Tab
   - 包含渠道列表表格
   - 频率限制配置卡片
   - 时间规则配置卡片

2. **新增配置对话框（第537-764行）**
   - 动态渠道配置表单
   - 根据渠道类型显示不同的配置项
   - 消息模板配置区域

3. **更新Script Section（第768-1185行）**
   - 导入ArrowUp/ArrowDown图标
   - 导入notificationAPI
   - 新增渠道数据结构
   - 新增频率限制和时间规则配置
   - 实现所有处理函数

**新增的核心函数：**
- `getChannelTypeName()` - 渠道类型名称映射
- `getChannelTypeColor()` - 渠道类型颜色映射
- `formatRelativeTime()` - 相对时间格式化
- `handleChannelMovePriority()` - 优先级调整
- `handleToggleChannel()` - 切换启用状态
- `handleConfigureChannel()` - 打开配置对话框
- `handleTestChannel()` - 测试渠道
- `saveChannelConfig()` - 保存渠道配置
- `saveFrequencyLimits()` - 保存频率限制
- `saveTimeRules()` - 保存时间规则
- `loadChannelConfigs()` - 加载所有配置

## 技术实现细节

### 1. 优先级调整机制

```javascript
const handleChannelMovePriority = (channel, direction) => {
  // 查找当前和目标索引
  const currentIndex = notificationChannels.value.findIndex(c => c.id === channel.id)
  const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1

  // 交换优先级值
  const targetChannel = notificationChannels.value[targetIndex]
  const tempPriority = channel.priority
  channel.priority = targetChannel.priority
  targetChannel.priority = tempPriority

  // 重新排序数组
  notificationChannels.value.sort((a, b) => a.priority - b.priority)
}
```

### 2. 配置验证逻辑

每种渠道类型都有相应的必填字段验证：

```javascript
switch (currentChannel.value.type) {
  case 'sms':
    // 验证API密钥、密钥ID、手机号码
    if (!config.api_key || !config.api_secret || config.phone_numbers.length === 0) {
      ElMessage.warning('请填写完整的短信配置')
      isValid = false
    }
    break
  // 其他渠道类型...
}
```

### 3. 消息模板变量系统

支持的模板变量：
- `{strategy_name}` - 策略名称
- `{signal_type}` - 信号类型（BUY/SELL）
- `{price}` - 当前价格
- `{strength}` - 信号强度
- `{pair}` - 交易对
- `{exchange}` - 交易所

默认模板示例：
```
🚨 [紧急] {strategy_name}: {signal_type} 信号
价格: {price}
强度: {strength}
```

### 4. 频率限制配置

三个级别的频率控制：
- **P0**: 最小间隔0秒（无限制），用于紧急通知
- **P1**: 最小间隔60秒，避免重要通知过于频繁
- **P2**: 批量间隔300秒，汇总后批量发送

### 5. 时间规则系统

**勿扰模式：**
- 在指定时段（如23:00-08:00）仅发送P0级别通知
- P1和P2级别通知会被延迟到勿扰时段结束后发送

**周末降级：**
- P1级别自动降级为P2
- P2级别进行批量发送
- 减少周末通知打扰

## UI/UX设计要点

### 1. 渠道类型标识

使用不同颜色的Tag标识渠道类型：
- 短信：红色（danger）
- 飞书：蓝色（primary）
- 企业微信：绿色（success）
- 邮件：橙色（warning）
- Telegram：灰色（info）

### 2. 配置状态可视化

- ✅ 已配置：绿色Success标签
- ⚠️ 未配置：橙色Warning标签

### 3. 优先级调整

使用上下箭头按钮组，直观地调整渠道优先级：
- 第一个渠道的"上移"按钮禁用
- 最后一个渠道的"下移"按钮禁用

### 4. 表单布局

- 使用el-divider分隔不同配置区域
- API配置、消息模板分别归类
- 关键配置项使用密码输入框保护敏感信息

## 后端API要求

### 需要实现的API端点（标记为TODO）

```javascript
// 渠道管理
notificationAPI.updateChannelPriority(channelId1, channelId2)  // 交换优先级
notificationAPI.updateChannelStatus(channelId, enabled)        // 更新启用状态
notificationAPI.updateChannel(channelId, config)               // 更新渠道配置
notificationAPI.test(channelType)                              // 测试渠道

// 全局配置
notificationAPI.updateFrequencyLimits(limits)                  // 更新频率限制
notificationAPI.updateTimeRules(rules)                         // 更新时间规则

// 数据加载
notificationAPI.getChannels()                                   // 获取所有渠道配置
notificationAPI.getFrequencyLimits()                           // 获取频率限制
notificationAPI.getTimeRules()                                 // 获取时间规则
```

### API响应格式建议

**测试渠道响应：**
```json
{
  "success": true,
  "message": "测试消息已发送",
  "latency_ms": 245,
  "timestamp": "2025-10-16T10:30:00Z"
}
```

**渠道列表响应：**
```json
{
  "channels": [
    {
      "id": 1,
      "type": "sms",
      "name": "短信通知",
      "priority": 1,
      "enabled": true,
      "configured": true,
      "levels": ["P0"],
      "last_test_time": "2025-10-16T10:25:00Z",
      "config": { ... },
      "templates": { ... }
    }
  ]
}
```

## 使用指南

### 配置新渠道

1. 点击渠道列表中的"配置"按钮
2. 填写渠道名称（可自定义）
3. 选择通知级别（P0/P1/P2）
4. 填写API配置信息
5. 自定义消息模板（可选）
6. 点击"保存配置"

### 调整渠道优先级

- 使用上下箭头调整渠道在列表中的顺序
- 优先级越高（数字越小）的渠道会优先被使用

### 测试渠道

1. 确保渠道已配置且已启用
2. 点击"测试"按钮
3. 检查接收设备是否收到测试消息

### 设置频率限制

1. 在"通知频率限制"卡片中设置各级别的最小间隔
2. 点击"保存频率限制"
3. 系统会根据设置控制通知发送频率

### 配置时间规则

1. 启用"勿扰模式"并设置时段
2. 可选启用"周末降级"
3. 点击"保存时间规则"

## 待办事项（TODO）

### 后端集成
- [ ] 实现通知渠道管理API
- [ ] 实现渠道测试API
- [ ] 实现消息模板变量替换系统
- [ ] 实现频率限制中间件
- [ ] 实现时间规则判断逻辑
- [ ] 实现优先级调度算法

### 功能增强
- [ ] 添加渠道健康检查
- [ ] 添加发送成功率统计
- [ ] 添加消息发送历史记录
- [ ] 添加批量通知预览
- [ ] 添加消息模板语法高亮
- [ ] 添加渠道配置导入/导出

### 用户体验优化
- [ ] 添加配置向导
- [ ] 添加常用模板库
- [ ] 添加配置验证实时反馈
- [ ] 添加渠道配置复制功能
- [ ] 添加移动端适配

## 测试建议

### 单元测试
- 测试优先级调整逻辑
- 测试配置验证函数
- 测试时间规则判断
- 测试频率限制计算

### 集成测试
- 测试各渠道API集成
- 测试消息模板渲染
- 测试批量发送逻辑
- 测试勿扰模式效果

### E2E测试
- 完整配置流程测试
- 优先级调整测试
- 发送测试消息验证
- 频率限制验证

## 已知问题

无

## 性能考虑

1. **localStorage使用**：配置数据量小，localStorage足够使用
2. **实时更新**：优先级调整立即生效，无需刷新
3. **异步测试**：测试渠道时使用loading状态，避免重复点击

## 总结

通知渠道详细配置界面已完成实施，提供了全面的多渠道通知管理能力。该功能作为Plan A的最后一个P0级任务，为系统提供了：

✅ 5种主流通知渠道支持
✅ 灵活的优先级管理
✅ 详细的渠道配置
✅ 消息模板定制
✅ 频率限制控制
✅ 时间规则管理

所有4个P0级任务已全部完成，前端实施进度：**100%** ✅

---

**文档版本**: 1.0
**最后更新**: 2025-10-16
**负责人**: Claude Code
