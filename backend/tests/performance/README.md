# 性能测试使用指南
# Performance Testing Guide

## 概述

BTC Watcher项目使用**Locust**进行性能测试，这是一个易于使用、可扩展的负载测试工具。

## 目录结构

```
tests/performance/
├── __init__.py                      # 包初始化
├── config.py                        # 性能测试配置
├── base_user.py                     # 基础用户类
├── test_auth_performance.py         # 认证API性能测试
├── test_strategy_performance.py     # 策略管理API性能测试
├── test_signal_performance.py       # 信号监控API性能测试
├── reports/                         # 测试报告目录
└── logs/                           # 日志目录

locustfile.py                        # 主测试文件（根目录）
```

## 快速开始

### 1. 安装依赖

```bash
# 安装Locust
pip install locust

# 或使用requirements文件
pip install -r requirements-performance.txt
```

### 2. 启动后端服务

```bash
# 确保后端API运行在 http://localhost:8000
cd backend
python -m uvicorn main:app --reload
```

### 3. 运行性能测试

#### 方式一: Web UI模式（推荐）

```bash
# 启动Locust Web UI
locust -f locustfile.py --host=http://localhost:8000

# 打开浏览器访问
# http://localhost:8089
```

**在Web UI中:**
1. 设置用户数 (Number of users)
2. 设置孵化速率 (Spawn rate)
3. 点击 "Start swarming"
4. 实时查看测试结果和图表

#### 方式二: 无头模式（命令行）

```bash
# 快速烟雾测试 (10用户, 1分钟)
locust -f locustfile.py --headless --users 10 --spawn-rate 2 --run-time 1m

# 负载测试 (100用户, 5分钟)
locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m

# 压力测试 (500用户, 10分钟)
locust -f locustfile.py --headless --users 500 --spawn-rate 50 --run-time 10m

# 生成报告
locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m \
       --csv=tests/performance/reports/perf \
       --html=tests/performance/reports/report.html
```

## 测试场景

### 1. 综合场景（默认）

```bash
# 使用locustfile.py - 真实用户行为模拟
locust -f locustfile.py
```

**包含:**
- 查看仪表盘 (权重: 10)
- 浏览策略 (权重: 8)
- 监控信号 (权重: 8)
- 管理策略 (权重: 3)
- 查看统计 (权重: 2)

### 2. 认证性能测试

```bash
# 测试登录和认证性能
locust -f tests/performance/test_auth_performance.py
```

**测试内容:**
- 用户登录
- Token验证
- 无效凭证处理
- 高并发认证

**用户类:**
- `AuthenticationUser` - 登录测试
- `AuthenticatedReadUser` - 已认证读操作
- `HighConcurrencyAuthUser` - 高并发测试

### 3. 策略管理性能测试

```bash
# 测试策略CRUD操作性能
locust -f tests/performance/test_strategy_performance.py
```

**测试内容:**
- 策略列表查询
- 策略创建/更新/删除
- 策略启动/停止
- 策略详情查询

**用户类:**
- `StrategyReadUser` - 读操作
- `StrategyWriteUser` - 写操作
- `StrategyOperationsUser` - 启动/停止操作
- `StrategyMixedUser` - 混合操作

### 4. 信号监控性能测试

```bash
# 测试信号查询和Webhook性能
locust -f tests/performance/test_signal_performance.py
```

**测试内容:**
- 信号列表查询
- 信号过滤（交易对、操作、强度）
- Webhook接收
- 统计信息查询

**用户类:**
- `SignalReadUser` - 读操作
- `SignalWebhookUser` - Webhook测试
- `SignalComplexQueryUser` - 复杂查询
- `SignalMixedUser` - 混合操作

## 测试类型

### 1. 烟雾测试 (Smoke Test)

验证基本功能在低负载下正常工作。

```bash
locust -f locustfile.py --headless --users 10 --spawn-rate 2 --run-time 1m
```

**目标:**
- 用户数: 10
- 持续时间: 1分钟
- 验证: 无错误

### 2. 负载测试 (Load Test)

测试系统在预期负载下的性能。

```bash
locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m
```

**目标:**
- 用户数: 100
- 持续时间: 5分钟
- 响应时间: < 300ms (good), < 1000ms (acceptable)
- 错误率: < 1%

### 3. 压力测试 (Stress Test)

测试系统在高负载下的表现和极限。

```bash
locust -f locustfile.py --headless --users 500 --spawn-rate 50 --run-time 10m
```

**目标:**
- 用户数: 500
- 持续时间: 10分钟
- 找出系统瓶颈
- 观察降级行为

### 4. 峰值测试 (Spike Test)

测试系统处理突发流量的能力。

```bash
locust -f locustfile.py --headless --users 1000 --spawn-rate 200 --run-time 3m
```

**目标:**
- 用户数: 1000
- 快速增长: 200 users/sec
- 持续时间: 3分钟
- 验证系统恢复能力

## 性能目标

### 响应时间目标

| 级别 | 响应时间 | 说明 |
|------|---------|------|
| **优秀** | < 100ms | 理想状态 |
| **良好** | < 300ms | 可接受 |
| **可用** | < 1000ms | 基本可用 |
| **较差** | > 1000ms | 需要优化 |

### 吞吐量目标

| 操作类型 | 目标 (req/s) | 说明 |
|---------|-------------|------|
| **读操作** | 1000 | 列表查询、详情查看 |
| **写操作** | 100 | 创建、更新、删除 |
| **认证操作** | 50 | 登录、Token验证 |

### 错误率目标

| 级别 | 错误率 | 说明 |
|------|-------|------|
| **可接受** | < 1% | 正常运行 |
| **警告** | < 5% | 需要关注 |
| **严重** | > 5% | 需要修复 |

## 高级用法

### 1. 指定特定用户类

```bash
# 只测试认证性能
locust -f tests/performance/test_auth_performance.py AuthenticationUser

# 只测试策略读操作
locust -f tests/performance/test_strategy_performance.py StrategyReadUser
```

### 2. 自定义配置

```bash
# 修改API基础URL
export API_BASE_URL="http://production-api.example.com:8000"
locust -f locustfile.py

# 修改测试用户
# 编辑 tests/performance/config.py
```

### 3. 分布式测试

**主节点:**
```bash
locust -f locustfile.py --master --expect-workers=3
```

**工作节点 (在不同机器上):**
```bash
locust -f locustfile.py --worker --master-host=<master-ip>
```

### 4. 自定义测试场景

创建自定义测试文件:

```python
# my_custom_test.py
from tests.performance.base_user import BTCWatcherUser
from locust import task, between

class MyCustomUser(BTCWatcherUser):
    wait_time = between(1, 3)

    @task
    def my_custom_scenario(self):
        # 自定义测试逻辑
        response = self.api_get("/strategies/")
        # ...
```

运行:
```bash
locust -f my_custom_test.py MyCustomUser
```

## 结果分析

### 1. Web UI报告

访问 `http://localhost:8089` 查看实时统计:

- **Statistics** - 请求统计（RPS, 响应时间, 错误率）
- **Charts** - 实时图表（响应时间趋势, RPS趋势）
- **Failures** - 失败请求详情
- **Exceptions** - 异常信息
- **Download Data** - 下载CSV数据

### 2. HTML报告

```bash
# 生成HTML报告
locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m \
       --html=tests/performance/reports/report.html
```

### 3. CSV报告

```bash
# 生成CSV文件
locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m \
       --csv=tests/performance/reports/perf

# 生成文件:
# - perf_stats.csv (统计数据)
# - perf_stats_history.csv (历史数据)
# - perf_failures.csv (失败记录)
```

### 4. 关键指标

查看报告时关注以下指标:

- **Total Requests** - 总请求数
- **Fails** - 失败请求数
- **Median Response Time** - 中位数响应时间
- **95th Percentile** - 95%请求的响应时间
- **Average RPS** - 平均每秒请求数
- **Fail Ratio** - 失败率

## 调试和故障排查

### 1. 启用详细日志

```python
# 在测试文件中
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 使用catch_response

```python
with self.client.get("/api/v1/strategies/", catch_response=True) as response:
    if response.status_code != 200:
        response.failure(f"Got status {response.status_code}")
    elif "error" in response.text:
        response.failure("Response contains error")
    else:
        response.success()
```

### 3. 添加断点

```python
@task
def my_test(self):
    import pdb; pdb.set_trace()
    # 调试代码
```

### 4. 监控系统资源

```bash
# 监控CPU和内存
htop

# 监控网络
sudo iftop

# 监控数据库
# 使用数据库自带的监控工具
```

## 最佳实践

### 1. 测试策略

✅ **逐步增加负载**
- 从小负载开始（10用户）
- 逐步增加到目标负载（100, 500, 1000）
- 观察每个阶段的系统行为

✅ **测试不同场景**
- 读密集型场景
- 写密集型场景
- 混合场景
- 峰值场景

✅ **长时间稳定性测试**
- 运行至少5-10分钟
- 观察内存泄漏
- 检查资源累积

### 2. 环境准备

✅ **独立测试环境**
- 使用专门的性能测试环境
- 避免在生产环境直接测试

✅ **数据准备**
- 预先创建足够的测试数据
- 模拟真实的数据规模

✅ **基准测试**
- 在优化前建立性能基准
- 优化后对比改善效果

### 3. 结果解读

✅ **关注趋势**
- 响应时间随负载的变化趋势
- 吞吐量的增长曲线
- 错误率的变化

✅ **识别瓶颈**
- 数据库查询慢
- API处理慢
- 网络延迟
- 资源耗尽

## 常见问题

### Q: 测试时出现连接错误？

A:
1. 确认后端服务运行: `curl http://localhost:8000/api/v1/strategies/`
2. 检查防火墙设置
3. 增加连接超时时间

### Q: 响应时间异常高？

A:
1. 检查数据库性能
2. 查看API日志
3. 减少并发用户数
4. 使用性能分析工具（如cProfile）

### Q: 如何模拟真实的负载模式？

A:
1. 分析生产环境的访问日志
2. 确定各操作的权重比例
3. 使用`@task(weight)`设置权重
4. 调整`wait_time`模拟用户思考时间

### Q: 测试结果不稳定？

A:
1. 增加预热时间
2. 延长测试持续时间
3. 多次运行取平均值
4. 检查网络抖动

## 参考资源

- [Locust官方文档](https://docs.locust.io/)
- [Locust最佳实践](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [性能测试指南](https://www.perfmatrix.com/performance-testing-guide/)

## 联系支持

如有问题或建议，请查看项目文档或联系开发团队。

---

**最后更新:** 2025-10-14
**维护者:** BTC Watcher团队
