# BTC Watcher Alpha测试指南
# Alpha Testing Guide

**版本**: v1.0.0
**测试阶段**: Alpha (内部测试)
**更新日期**: 2025-10-16

---

## 欢迎参加BTC Watcher Alpha测试！

感谢您参与BTC Watcher的Alpha测试。本指南将帮助您快速了解系统并开始测试。

---

## 📋 测试须知

### 重要说明

⚠️ **这是Alpha测试版本，存在以下限制**:

1. **仅供内部测试使用** - 请勿在生产环境中使用
2. **请勿输入真实交易密钥** - 仅使用测试数据
3. **数据可能丢失** - 我们会尽量避免，但请做好准备
4. **功能可能变更** - 根据测试反馈，功能可能随时调整
5. **内网访问** - 系统仅在内网环境运行，不暴露到公网

### Alpha测试目标

- 验证核心功能是否正常工作
- 发现潜在的Bug和问题
- 收集用户体验反馈
- 评估系统性能和稳定性

### 测试时间

- **第一阶段** (Week 1-2): 3-5个内部用户，每天2-4小时测试
- **第二阶段** (Week 3-4): 扩展到5-10个用户（如果第一阶段顺利）

---

## 🚀 快速开始

### 1. 系统访问

**后端API服务**:
- URL: `http://localhost:8501`
- API文档: `http://localhost:8501/docs` (Swagger UI)
- 备用文档: `http://localhost:8501/redoc` (ReDoc)

**健康检查**:
```bash
curl http://localhost:8501/health
```

预期返回:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 2. 测试账号

您的测试账号信息（请妥善保管）:

| 用户名 | 密码 | 邮箱 | 用途 |
|--------|------|------|------|
| alpha1 | Alpha@2025 | alpha1@example.com | 内部测试人员 |
| alpha2 | Alpha@2025 | alpha2@example.com | 内部测试人员 |
| alpha3 | Alpha@2025 | alpha3@example.com | 友好用户测试 |
| tester | Test@2025 | tester@example.com | 测试管理员 |
| demo | Demo@2025 | demo@example.com | 演示账号 |

**注**: 所有账号已激活，可以直接使用。

### 3. 登录获取Token

**方法1: 使用API文档 (推荐新手)**

1. 访问 `http://localhost:8501/docs`
2. 找到 `POST /api/v1/auth/token` 端点
3. 点击 "Try it out"
4. 填写用户名和密码
5. 点击 "Execute"
6. 复制返回的 `access_token`

**方法2: 使用curl命令**

```bash
# 登录获取Token
curl -X POST "http://localhost:8501/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alpha1&password=Alpha@2025"
```

返回示例:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

保存这个 `access_token`，后续所有API请求都需要使用它。

### 4. 使用Token访问API

将Token添加到请求头中:

```bash
# 查看当前用户信息
curl -X GET "http://localhost:8501/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**在Swagger UI中**:
1. 点击页面右上角的 "Authorize" 按钮
2. 输入: `Bearer YOUR_ACCESS_TOKEN`
3. 点击 "Authorize"
4. 之后所有请求都会自动带上Token

---

## 🎯 核心功能测试

### 1. 用户认证

**测试项目**:
- [x] 用户登录
- [x] 获取用户信息
- [x] 修改密码（可选）
- [x] 登出

**测试步骤**:

```bash
# 1. 登录
TOKEN=$(curl -s -X POST "http://localhost:8501/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alpha1&password=Alpha@2025" | jq -r '.access_token')

# 2. 查看用户信息
curl -X GET "http://localhost:8501/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 3. 登出
curl -X POST "http://localhost:8501/api/v1/auth/logout" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. 策略管理

**测试项目**:
- [ ] 创建交易策略
- [ ] 查看策略列表
- [ ] 查看单个策略详情
- [ ] 启动/停止策略
- [ ] 更新策略配置
- [ ] 删除策略

**测试步骤**:

```bash
# 1. 创建策略
curl -X POST "http://localhost:8501/api/v1/strategies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC突破策略",
    "description": "当BTC价格突破关键阻力位时买入",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "config": {
      "entry_signal": "price_breakout",
      "resistance_level": 45000
    }
  }' | python -m json.tool

# 2. 查看策略列表
curl -X GET "http://localhost:8501/api/v1/strategies" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 3. 启动策略（假设策略ID为1）
curl -X POST "http://localhost:8501/api/v1/strategies/1/start" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 4. 停止策略
curl -X POST "http://localhost:8501/api/v1/strategies/1/stop" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 5. 删除策略
curl -X DELETE "http://localhost:8501/api/v1/strategies/1" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. 交易信号

**测试项目**:
- [ ] 查看交易信号列表
- [ ] 查看单个信号详情
- [ ] 信号筛选（按策略、状态等）
- [ ] 信号统计分析

**测试步骤**:

```bash
# 1. 查看所有信号
curl -X GET "http://localhost:8501/api/v1/signals" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 2. 查看特定策略的信号（假设策略ID为1）
curl -X GET "http://localhost:8501/api/v1/signals?strategy_id=1" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 3. 查看单个信号详情（假设信号ID为1）
curl -X GET "http://localhost:8501/api/v1/signals/1" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 4. 信号统计
curl -X GET "http://localhost:8501/api/v1/signals/stats" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### 4. 通知系统

**测试项目**:
- [ ] 配置Telegram通知
- [ ] 配置邮件通知
- [ ] 配置企业微信通知
- [ ] 测试通知发送
- [ ] 查看通知历史

**测试步骤**:

```bash
# 1. 查看通知配置
curl -X GET "http://localhost:8501/api/v1/notifications/config" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 2. 更新通知配置
curl -X PUT "http://localhost:8501/api/v1/notifications/config" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_enabled": true,
    "telegram_bot_token": "YOUR_BOT_TOKEN",
    "telegram_chat_id": "YOUR_CHAT_ID"
  }' | python -m json.tool

# 3. 测试通知
curl -X POST "http://localhost:8501/api/v1/notifications/test" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### 5. 系统监控

**测试项目**:
- [ ] 查看系统状态
- [ ] 查看性能指标
- [ ] 查看容量使用情况
- [ ] WebSocket实时推送

**测试步骤**:

```bash
# 1. 系统健康检查
curl -X GET "http://localhost:8501/health" | python -m json.tool

# 2. 系统监控指标
curl -X GET "http://localhost:8501/api/v1/monitoring/metrics" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 3. 系统容量
curl -X GET "http://localhost:8501/api/v1/monitoring/capacity" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

---

## 🔧 已知问题和限制

### FreqTrade实例管理

⚠️ **状态**: 有限制
**问题**: FreqTrade实例无法在当前环境自动启动（权限问题）
**影响**: 无法通过API自动管理FreqTrade进程
**临时方案**:
- 手动启动FreqTrade实例
- 使用现有的FreqTrade实例
- Alpha阶段可以不依赖FreqTrade，使用模拟信号测试

### 前端界面

⚠️ **状态**: 未测试
**问题**: 前端代码已开发但未启动测试
**影响**: 用户界面可用性未验证
**临时方案**:
- Alpha阶段使用Swagger API文档进行测试
- 或使用Postman等API测试工具
- 前端测试将在后续阶段进行

### 策略批量创建

⚠️ **状态**: 不建议
**问题**: 高并发下策略创建可能失败
**影响**: 批量创建策略可能不稳定
**建议**:
- Alpha阶段单个创建策略
- 避免短时间内大量创建

### HTTPS/SSL

⚠️ **状态**: 未启用
**影响**: 数据传输未加密
**要求**:
- **仅在内网环境使用**
- **不暴露到公网**
- **不输入真实敏感信息**

---

## 📊 性能指标参考

根据性能优化测试，系统当前性能指标:

| 指标 | 当前值 | 评级 |
|------|--------|------|
| API平均响应时间 | 15 ms | ⭐⭐⭐⭐⭐ 优秀 |
| API P95响应时间 | < 20 ms | ⭐⭐⭐⭐⭐ 优秀 |
| API P99响应时间 | < 20 ms | ⭐⭐⭐⭐⭐ 优秀 |
| 认证操作 | < 20 ms | ⭐⭐⭐⭐⭐ 优秀 |
| 数据库查询 | < 5 ms | ⭐⭐⭐⭐⭐ 优秀 |
| 并发支持 | 10+ 用户 | ✅ 足够 |

**如果您遇到明显的性能问题（响应时间>100ms），请记录并反馈给我们。**

---

## 🐛 如何报告Bug

### Bug报告必须包含

1. **重现步骤**: 详细描述如何触发Bug
2. **预期行为**: 您认为应该发生什么
3. **实际行为**: 实际发生了什么
4. **错误信息**: 如果有，请复制完整的错误消息
5. **环境信息**:
   - 使用的账号
   - 请求的API端点
   - 测试时间

### Bug严重性分类

- **P0 (严重)**: 系统崩溃、数据丢失、安全漏洞
- **P1 (高)**: 核心功能无法使用
- **P2 (中)**: 功能可用但有明显问题
- **P3 (低)**: 小问题、UI问题、建议改进

### Bug报告示例

```
标题: 创建策略时返回500错误

严重性: P1

重现步骤:
1. 使用alpha1账号登录
2. 调用 POST /api/v1/strategies
3. 传入参数: {"name": "测试策略", "symbol": "BTC/USDT"}

预期结果: 成功创建策略，返回201

实际结果: 返回500错误，错误信息：
{
  "detail": "Internal Server Error"
}

测试环境:
- 账号: alpha1
- 时间: 2025-10-16 15:30
- API: POST /api/v1/strategies
```

---

## 💬 反馈渠道

### 问题反馈

- **Bug报告**: [在此提交]
- **功能建议**: [在此提交]
- **即时沟通**: [微信群/钉钉群]

### 反馈响应时间

- **P0严重问题**: 2小时内响应，24小时内修复
- **P1高优先级**: 4小时内响应，48小时内修复
- **P2中等问题**: 1个工作日内响应
- **P3低优先级**: 3个工作日内响应

---

## 📈 测试检查清单

### 每日测试任务

- [ ] 登录系统并验证Token有效
- [ ] 创建至少1个测试策略
- [ ] 查看信号列表
- [ ] 测试至少3个不同的API端点
- [ ] 记录遇到的任何问题

### 每周测试任务

- [ ] 完整测试一个业务流程（策略创建→启动→查看信号→停止）
- [ ] 测试通知系统配置
- [ ] 测试数据筛选和查询功能
- [ ] 提交本周测试总结和Bug报告

---

## 🔐 安全提醒

### 必须遵守

1. ✅ 仅在内网环境访问系统
2. ✅ 不要分享您的测试账号密码
3. ✅ 不要输入真实的交易所API密钥
4. ✅ 不要输入真实的资金账户信息
5. ✅ 不要尝试攻击或破坏系统

### 数据安全

- **数据备份**: 系统每日备份，但Alpha阶段数据不保证持久保存
- **数据隔离**: 每个用户的数据相互隔离
- **Token过期**: Token有效期24小时，过期需重新登录

---

## 📚 参考资料

### API文档

- **Swagger UI**: http://localhost:8501/docs
- **ReDoc**: http://localhost:8501/redoc

### 项目文档

- [性能优化报告](PERFORMANCE_OPTIMIZATION_REPORT.md)
- [Alpha就绪度评估](ALPHA_READINESS_ASSESSMENT.md)
- [单元测试报告](UNIT_TEST_FINAL_REPORT.md)

### 技术栈

- **后端**: FastAPI + Python 3.13
- **数据库**: PostgreSQL 18.0
- **缓存**: Redis latest
- **认证**: JWT Token

---

## ❓ 常见问题

### Q: Token过期怎么办？

A: Token有效期为24小时。过期后重新调用登录接口获取新Token即可。

### Q: 忘记密码怎么办？

A: Alpha阶段请联系管理员重置密码。

### Q: API返回401 Unauthorized错误？

A: 检查:
1. Token是否过期
2. Authorization头格式是否正确（`Bearer YOUR_TOKEN`）
3. 是否已经登出

### Q: 数据库中的测试数据会被清除吗？

A: Alpha测试期间，数据会尽量保留。但建议不要依赖长期保存，重要测试场景请记录下来。

### Q: 可以修改用户邮箱吗？

A: Alpha阶段暂不支持，如需修改请联系管理员。

### Q: 系统支持多少并发用户？

A: 当前配置支持10+并发用户，Alpha阶段限制在5-10个用户。

---

## 🎉 感谢您的参与！

您的测试和反馈对BTC Watcher的发展至关重要。如有任何问题，请随时联系我们。

**祝测试顺利！**

---

**文档版本**: v1.0.0
**最后更新**: 2025-10-16
**维护者**: BTC Watcher开发团队
