# 容量使用趋势 - 功能说明与优化

## 📊 功能定义

### 什么是"容量"？

**容量** = **策略运行容量** (Strategy Capacity)

这是指系统同时运行FreqTrade策略实例的能力。

### 容量计算公式

```
容量使用率 = (当前运行策略数 / 最大并发策略数) × 100%
```

**示例**：
- 当前运行: 25 个策略
- 最大并发: 1000 个策略
- 容量使用率: 25 / 1000 × 100% = 2.5%

### 容量组成

| 指标 | 说明 | 来源 |
|------|------|------|
| **max_strategies** | 最大并发策略数 (1000) | `freqtrade_manager.py:28` |
| **running_strategies** | 当前运行策略数 | 实时计数 |
| **available_slots** | 可用策略槽位数 | max - running |
| **utilization_percent** | 容量使用率 (%) | (running / max) × 100 |

### 为什么是1000？

系统配置了**1000个端口**（8081-9080），每个FreqTrade实例占用1个端口，因此最大并发策略数为1000。

---

## 🎨 前端优化内容

### 优化前的问题

1. ❌ **标签模糊**："容量使用趋势" - 不清楚是什么容量
2. ❌ **缺少说明**：没有解释容量的含义
3. ❌ **信息不足**：看不到当前运行数、可用数、最大数
4. ❌ **tooltip简陋**：只显示使用率百分比

### 优化后的改进

#### 1. 明确标签
```
容量使用趋势 → 策略容量使用趋势
```

#### 2. 添加说明提示图标
在标题旁边添加问号图标，hover显示详细说明：
```
容量说明：
当前运行策略数 / 最大并发策略数

● 运行中：25 个
● 可用：975 个
● 总计：1000 个
```

#### 3. 优化统计卡片
```
原标签: "容量使用率"
新标签: "策略容量" + 说明图标
说明: "当前运行策略数占最大并发数的比例"
```

#### 4. 增强图表tooltip
```
原tooltip: "时间<br/>使用率: 2.5%"
新tooltip: "时间
           ● 使用率: 2.5%
           ● 运行中: ~25 个策略"
```

#### 5. 添加警告线
在图表中添加80%容量警告线，提醒运维人员注意容量压力

---

## 🔧 技术实现

### 前端修改 (frontend/src/views/Dashboard.vue)

#### 导入图标
```javascript
import { QuestionFilled } from '@element-plus/icons-vue'
```

#### 图表配置增强
```javascript
capacityTrendOption: {
  // 添加网格配置
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  // 增强tooltip
  tooltip: {
    formatter: (params) => {
      const utilization = params[0].value
      const runningCount = Math.round((utilization / 100) * max_strategies)
      return `时间<br/>
              ● 使用率: ${utilization.toFixed(1)}%<br/>
              ● 运行中: ~${runningCount} 个策略`
    }
  },
  // 添加警告线
  series: [{
    markLine: {
      data: [
        { yAxis: 80, label: { formatter: '警告线 80%' } }
      ]
    }
  }]
}
```

---

## 📈 后端数据说明

### API端点

#### 1. 获取当前容量
```
GET /api/v1/system/capacity
```

**返回**：
```json
{
  "max_strategies": 1000,
  "running_strategies": 25,
  "available_slots": 975,
  "utilization_percent": 2.5,
  "port_range": "8081-9080",
  "can_start_more": true,
  "architecture": "multi_instance_reverse_proxy"
}
```

#### 2. 获取容量趋势
```
GET /api/v1/monitoring/capacity/trend?hours=24
```

**返回**：
```json
{
  "period_hours": 24,
  "data_points": [
    {
      "timestamp": "2025-10-16T10:00:00Z",
      "utilization_percent": 2.5,
      "running_strategies": 25,
      "available_slots": 975
    },
    ...
  ],
  "total_points": 48
}
```

### 后端当前状态

⚠️ **注意**：目前后端返回的是**模拟数据**或**空数据**

```python
# backend/api/v1/system.py:419
async def _get_capacity_trend_from_cache(hours: int) -> dict:
    """从缓存获取容量趋势数据"""
    # TODO: 实现从Redis或数据库获取历史数据
    return {
        "peak": 5.0,
        "average": 2.5,
        "trend": "stable",
        "data_points": []  # 空数据
    }
```

---

## 🚀 未来优化建议

### 1. 实现历史数据存储

**方案A: Redis时序数据**
```python
# 每分钟记录一次容量数据
import redis
import json
from datetime import datetime

async def record_capacity_snapshot():
    capacity = ft_manager.get_capacity_info()
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "utilization_percent": capacity["utilization_percent"],
        "running_strategies": capacity["running_strategies"]
    }
    
    # 使用Redis sorted set存储，score为timestamp
    await redis_client.zadd(
        "capacity:history",
        {json.dumps(snapshot): datetime.now().timestamp()}
    )
    
    # 保留最近7天数据
    cutoff = datetime.now().timestamp() - (7 * 24 * 3600)
    await redis_client.zremrangebyscore("capacity:history", 0, cutoff)
```

**方案B: 数据库表**
```python
class CapacitySnapshot(Base):
    __tablename__ = "capacity_snapshots"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True)
    utilization_percent = Column(Float)
    running_strategies = Column(Integer)
    available_slots = Column(Integer)
    created_at = Column(DateTime, default=func.now())
```

### 2. 添加容量告警

当容量使用率超过阈值时，自动发送通知：

```python
async def check_capacity_alert():
    capacity = ft_manager.get_capacity_info()
    
    if capacity["utilization_percent"] > 80:
        await notification_service.send_notification(
            user_id=1,
            title="⚠️ 策略容量告警",
            message=f"当前容量使用率: {capacity['utilization_percent']}%\n"
                   f"运行中: {capacity['running_strategies']}/{capacity['max_strategies']}",
            priority="P2",
            notification_type="alert"
        )
```

### 3. 添加容量预测

基于历史数据预测未来容量趋势：

```
当前增长率: +5 个策略/小时
预计12小时后达到80%容量
建议: 准备扩容或清理闲置策略
```

### 4. 添加容量详细分析

```
容量使用情况:
- 高频交易策略: 15 个 (60%)
- 中频交易策略: 8 个 (32%)
- 低频交易策略: 2 个 (8%)

按交易所分布:
- Binance: 18 个 (72%)
- OKX: 5 个 (20%)
- Huobi: 2 个 (8%)
```

---

## ✅ 修改文件清单

### 前端文件
- ✅ `frontend/src/views/Dashboard.vue`
  - 第68-91行: 图表标题和说明
  - 第138行: 导入QuestionFilled图标
  - 第149-200行: 优化capacityTrendOption配置
  - 第54-61行: 优化统计卡片标签

### 文档文件
- ✅ `CAPACITY_TREND_CLARIFICATION.md` - 本文档

---

## 📊 用户体验对比

### 优化前
- ❓ 用户: "容量是什么意思？"
- ❓ 用户: "这个趋势图显示的是什么？"
- ❓ 用户: "我怎么知道还能运行多少策略？"

### 优化后
- ✅ 用户: "策略容量使用趋势 - 清晰！"
- ✅ 用户: 鼠标hover查看详细说明
- ✅ 用户: tooltip显示当前运行数和使用率
- ✅ 用户: 看到警告线，知道80%是临界点

---

## 🎯 总结

### 问题
"容量使用趋势"含义不明确，用户不知道指的是什么容量。

### 解决方案
1. ✅ 明确标签为"策略容量使用趋势"
2. ✅ 添加说明tooltip，解释容量含义
3. ✅ 增强图表信息，显示运行策略数
4. ✅ 添加80%警告线
5. ✅ 优化统计卡片标签

### 后续工作
- ⏳ 实现真实历史数据存储（Redis或数据库）
- ⏳ 添加容量告警功能
- ⏳ 添加容量预测功能

---

**文档版本**: 1.0  
**创建时间**: 2025-10-16  
**作者**: Claude Code
