# 策略恢复机制文档

## 概述

策略恢复机制解决了后端重启后策略状态不一致的问题。当后端服务重启时，数据库中的策略状态会保留，但实际的FreqTrade进程已经终止。此机制可以自动恢复这些策略或重置它们的状态。

## 问题背景

### 重启前后的状态对比

**重启前：**
```
数据库：strategy_id=1, status='running'  ✅
内存：  self.strategy_processes[1] = <Process PID:12345>  ✅
进程：  FreqTrade PID 12345 正在运行  ✅
```

**重启后（无恢复机制）：**
```
数据库：strategy_id=1, status='running'  ✅ (仍然是running)
内存：  self.strategy_processes = {}  ❌ (空字典)
进程：  FreqTrade进程已终止  ❌
结果：  前端显示"error"状态  ❌
```

## 解决方案：混合恢复机制

### 方案特点

1. **智能恢复**: 优先尝试恢复运行中的策略
2. **容错机制**: 恢复失败时自动重置状态
3. **可配置**: 通过环境变量控制行为
4. **详细日志**: 完整的恢复过程记录

## 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# 是否启用自动恢复
# true: 启动时自动恢复所有运行中的策略 (推荐生产环境)
# false: 启动时将所有策略状态重置为stopped (开发/测试环境)
AUTO_RECOVER_STRATEGIES=true

# 策略恢复超时时间（秒）
RECOVERY_TIMEOUT=300

# 单个策略最大重试次数
MAX_RECOVERY_RETRIES=2
```

### 配置建议

| 环境 | AUTO_RECOVER | 说明 |
|------|-------------|------|
| **生产环境** | `true` | 自动恢复，最小化人工干预 |
| **测试环境** | `false` | 重置状态，避免意外恢复 |
| **开发环境** | `false` | 手动控制策略启动 |

## 工作流程

### 1. 自动恢复模式 (AUTO_RECOVER_STRATEGIES=true)

```
启动应用
    ↓
初始化FreqTrade Manager
    ↓
查询数据库中status='running'的策略
    ↓
对每个策略：
    ├─ 尝试启动FreqTrade进程
    ├─ 等待API就绪
    ├─ 验证健康状态
    ├─ 成功 → 标记为recovered
    └─ 失败 → 重试 → 最终失败 → 重置为stopped
    ↓
记录恢复摘要日志
```

### 2. 重置模式 (AUTO_RECOVER_STRATEGIES=false)

```
启动应用
    ↓
初始化FreqTrade Manager
    ↓
将所有status='running'的策略重置为stopped
    ↓
记录重置数量
```

## 日志示例

### 自动恢复成功

```
============================================================
Starting Strategy Recovery (AUTO_RECOVER_STRATEGIES=True)
============================================================
Starting strategy recovery process...
Found 3 strategies in 'running' state
Attempting to recover strategy 1: BTC-USDT-MA-Cross
✅ Successfully recovered strategy 1
Attempting to recover strategy 2: ETH-USDT-RSI
✅ Successfully recovered strategy 2
Attempting to recover strategy 3: ADA-USDT-MACD
✅ Successfully recovered strategy 3
==================================================
Strategy Recovery Summary:
  Total strategies found: 3
  Successfully recovered: 3
  Failed and reset: 0
==================================================
📊 Recovery Results:
   ✅ Recovered: 3
   ❌ Failed: 0
   🔄 Reset: 0
✅ No strategies needed recovery
============================================================
```

### 部分恢复失败

```
============================================================
Starting Strategy Recovery (AUTO_RECOVER_STRATEGIES=True)
============================================================
Starting strategy recovery process...
Found 2 strategies in 'running' state
Attempting to recover strategy 1: BTC-USDT-MA-Cross
✅ Successfully recovered strategy 1
Attempting to recover strategy 2: ETH-USDT-RSI
Failed to recover strategy 2, retry 1/2
Failed to recover strategy 2, retry 2/2
❌ Failed to recover strategy 2 after 2 attempts, resetting to 'stopped'
==================================================
Strategy Recovery Summary:
  Total strategies found: 2
  Successfully recovered: 1
  Failed and reset: 1
==================================================
📊 Recovery Results:
   ✅ Recovered: 1
   ❌ Failed: 1
   🔄 Reset: 1
⚠️  Some strategies could not be recovered and were reset to 'stopped'
   - Strategy 2 (ETH-USDT-RSI)
============================================================
```

### 重置模式

```
============================================================
AUTO_RECOVER_STRATEGIES=False - Resetting all strategies
============================================================
Reset 3 strategies to 'stopped' status
✅ Reset 3 strategies to 'stopped' status
============================================================
```

## API 接口

### 手动触发恢复（未来功能）

```http
POST /api/v1/strategies/recover
```

**响应示例：**
```json
{
  "success": true,
  "results": {
    "total_found": 3,
    "recovered": 2,
    "failed": 1,
    "reset": 1,
    "details": [
      {
        "strategy_id": 1,
        "name": "BTC-USDT-MA-Cross",
        "status": "recovered",
        "retries": 0
      },
      {
        "strategy_id": 2,
        "name": "ETH-USDT-RSI",
        "status": "failed_and_reset",
        "retries": 2
      }
    ]
  }
}
```

## 故障排查

### 问题1: 所有策略恢复失败

**可能原因：**
- FreqTrade未正确安装
- 端口被占用
- 配置文件错误
- 数据库连接问题

**解决方法：**
1. 检查日志：`tail -f backend/logs/app.log`
2. 验证FreqTrade安装：`freqtrade --version`
3. 检查端口占用：`lsof -i :8081-9080`
4. 测试数据库连接

### 问题2: 策略恢复缓慢

**可能原因：**
- 策略数量过多
- 网络延迟
- 资源不足

**解决方法：**
1. 减少并发策略数量
2. 增加 `RECOVERY_TIMEOUT` 值
3. 升级服务器资源

### 问题3: 状态不一致

**症状：**
- 数据库显示running
- 但实际进程不存在

**解决方法：**
1. 重启后端服务（会自动恢复或重置）
2. 或手动重置状态：
```bash
# 进入数据库
psql -U btc_user -d btc_watcher

# 重置所有策略状态
UPDATE strategies SET status = 'stopped' WHERE status = 'running';
```

## 性能影响

### 启动时间增加

| 策略数量 | 预计增加时间 |
|---------|------------|
| 1-10 | +10-30秒 |
| 11-50 | +30-90秒 |
| 51-100 | +90-180秒 |
| 100+ | +180秒以上 |

### 资源使用

- **CPU**: 恢复期间CPU使用率会短暂上升20-40%
- **内存**: 每个策略约需50-100MB内存
- **网络**: FreqTrade API初始化需要网络连接

## 最佳实践

1. **生产环境**
   - 启用自动恢复 (`AUTO_RECOVER_STRATEGIES=true`)
   - 设置合理的重试次数 (2-3次)
   - 监控恢复日志

2. **开发环境**
   - 禁用自动恢复 (`AUTO_RECOVER_STRATEGIES=false`)
   - 手动控制策略启动
   - 避免意外资源占用

3. **监控告警**
   - 监控恢复成功率
   - 恢复失败时发送告警
   - 定期检查策略健康状态

4. **定期维护**
   - 清理长期stopped的策略
   - 优化策略配置
   - 升级FreqTrade版本

## 相关文档

- [DESIGN.md](../DESIGN.md) - 系统架构设计
- [API文档](http://localhost:8000/docs) - 完整API接口
- [FreqTrade文档](https://www.freqtrade.io/en/stable/) - FreqTrade官方文档

## 更新历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2025-10-26 | 初始版本，实现混合恢复机制 |
