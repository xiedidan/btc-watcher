# 优先级定义修改文档

## 修改说明

根据需求，将优先级定义从"P0最高"改为"P0最低"，具体修改如下：

## 新的优先级定义

| 优先级 | 紧急程度 | 说明 | 发送方式 | 最小间隔 |
|--------|---------|------|---------|---------|
| **P2** | 最高（紧急） | 紧急通知，需要立即处理 | 立即发送 | 0秒（无限制） |
| **P1** | 中等（重要） | 重要通知，需要及时关注 | 实时发送 | 60秒 |
| **P0** | 最低（一般） | 一般通知，可延迟处理 | 批量发送 | 300秒 |

## 修改对照表

| 原定义 | 新定义 | 变更 |
|--------|--------|------|
| P0 - 紧急通知（立即发送） | P2 - 紧急通知（立即发送） | P0→P2 |
| P1 - 重要通知（实时发送） | P1 - 重要通知（实时发送） | 不变 |
| P2 - 一般通知（批量发送） | P0 - 一般通知（批量发送） | P2→P0 |

## 配置项修改

### 频率限制
- ~~P0最小间隔~~ → **P2最小间隔**：0秒（紧急通知无限制）
- **P1最小间隔**：60秒（重要通知）
- ~~P2批量间隔~~ → **P0批量间隔**：300秒（一般通知）

### 时间规则
- 勿扰模式：仅发送**P2**级别通知（最高优先级）
- 周末降级：P1降级为P0，P0通知批量发送

### 渠道配置
- SMS（短信）：适用P2（紧急通知）
- Feishu（飞书）：适用P2/P1（紧急/重要通知）
- WeChat（企业微信）：适用P2/P1/P0（全级别通知）
- Email（邮件）：适用P1/P0（重要/一般通知）
- Telegram：适用P2/P1（紧急/重要通知）

## 信号阈值映射

### 策略配置中的阈值
- 强烈信号（≥0.8）→ **P2**（紧急通知，立即发送）🔴
- 中等信号（≥0.6）→ **P1**（重要通知，实时发送）🟠
- 弱信号（≥0.4）→ **P0**（一般通知，批量发送）🟡

## UI显示

### Tag颜色
- P2：`type="danger"` 红色 🔴
- P1：`type="warning"` 橙色 🟠
- P0：`type="info"` 灰色 🟡

### 描述文本
- P2：紧急通知（立即发送）
- P1：重要通知（实时发送）
- P0：一般通知（批量发送）

## 代码示例

### 前端判断逻辑
```javascript
// 根据信号强度确定优先级
function getPriorityLevel(strength, thresholds) {
  if (strength >= thresholds.strong) {
    return 'P2'  // 紧急（原P0）
  } else if (strength >= thresholds.medium) {
    return 'P1'  // 重要
  } else if (strength >= thresholds.weak) {
    return 'P0'  // 一般（原P2）
  }
  return null  // 低于阈值，不发送
}
```

### 后端优先级排序
```python
# 优先级排序（P2最高，P0最低）
priority_order = {'P2': 2, 'P1': 1, 'P0': 0}
sorted_notifications = sorted(
    notifications,
    key=lambda x: priority_order.get(x.priority, 0),
    reverse=True
)
```

## 需要修改的文件清单

### 前端文件
- ✅ `frontend/src/views/Settings.vue` - 通知渠道配置
- ✅ `frontend/src/views/Strategies.vue` - 策略阈值配置
- ✅ `frontend/src/views/Signals.vue` - 信号优先级显示

### 文档文件
- ✅ `NOTIFICATION_CHANNEL_IMPLEMENTATION.md`
- ✅ `BUSINESS_FLOW_DESIGN.md`
- ✅ `FINAL_SUMMARY.md`
- ✅ `BACKEND_API_SUPPORT_REPORT.md`
- ✅ `PROJECT_COMPLETION_REPORT.md`
- ✅ `DETAILED_DESIGN.md`

### 后端文件
- ✅ `backend/tests/unit/test_notification_service.py`

## 注意事项

1. **数据库迁移**：如果数据库中已有数据，需要执行迁移脚本转换优先级值
2. **API兼容性**：确保API文档同步更新
3. **测试用例**：更新所有涉及优先级的测试用例
4. **用户通知**：发布时需要通知用户优先级定义的变更

---

**文档版本**: 1.0
**创建日期**: 2025-10-16
**状态**: 待实施
