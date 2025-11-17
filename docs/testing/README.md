# BTC Watcher Testing Guide
# 测试指南

## 📋 目录

1. [测试环境准备](#测试环境准备)
2. [运行测试](#运行测试)
3. [测试类型](#测试类型)
4. [部署验证](#部署验证)
5. [故障排查](#故障排查)

---

## 测试环境准备

### 1. 安装测试依赖

```bash
cd backend
pip install -r requirements-test.txt
```

### 2. 确保Docker环境运行

```bash
# 启动所有服务
docker-compose up -d

# 验证服务状态
docker ps
```

---

## 运行测试

### API集成测试

```bash
# 运行所有API测试
cd backend
python tests/test_api.py

# 或使用pytest
pytest tests/test_api.py -v
```

### 部署前验证

```bash
# 验证部署环境（在启动前运行）
./verify_deployment.sh
```

### 运行时验证

```bash
# 验证运行中的服务（启动后运行）
./scripts/verify_runtime.sh
```

---

## 测试类型

### 1. Smoke Tests（冒烟测试）

快速验证核心功能是否正常工作：

```bash
# 健康检查
curl http://localhost:8000/api/v1/system/health

# API文档可访问性
curl http://localhost:8000/docs

# 前端可访问性
curl http://localhost
```

### 2. Integration Tests（集成测试）

测试各个模块之间的交互：

```bash
python backend/tests/test_api.py
```

测试包括：
- ✅ 用户注册和登录
- ✅ 策略CRUD操作
- ✅ 系统容量查询
- ✅ 认证和授权

### 3. Manual Tests（手动测试）

#### 测试用户注册

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "test123456"
  }'
```

#### 测试用户登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=test123456"
```

#### 测试创建策略

```bash
# 先登录获取token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# 创建策略
curl -X POST http://localhost:8000/api/v1/strategies/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Strategy",
    "strategy_class": "SampleStrategy",
    "exchange": "binance",
    "timeframe": "1h",
    "pair_whitelist": ["BTC/USDT"],
    "dry_run": true,
    "signal_thresholds": {
      "strong": 0.8,
      "medium": 0.6,
      "weak": 0.4
    }
  }'
```

#### 测试系统容量

```bash
curl -X GET http://localhost:8000/api/v1/system/capacity \
  -H "Authorization: Bearer $TOKEN"
```

---

## 部署验证

### 完整部署验证流程

```bash
# 1. 验证部署环境
./verify_deployment.sh

# 2. 启动服务
./scripts/start.sh

# 3. 等待服务启动（约30秒）
sleep 30

# 4. 验证运行时
./scripts/verify_runtime.sh

# 5. 运行API测试
cd backend && python tests/test_api.py
```

### 检查项目

部署验证会检查：
- ✅ Docker和Docker Compose安装
- ✅ 项目文件完整性
- ✅ 环境配置文件
- ✅ 端口占用情况
- ✅ Docker Compose配置语法
- ✅ 必要的数据目录

运行时验证会检查：
- ✅ 所有容器运行状态
- ✅ 后端API响应
- ✅ 前端访问
- ✅ 数据库连接
- ✅ Redis连接
- ✅ 日志中的错误

---

## 故障排查

### 问题1: 容器无法启动

```bash
# 查看容器状态
docker ps -a

# 查看容器日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db

# 重启容器
docker-compose restart
```

### 问题2: API无法访问

```bash
# 检查后端容器
docker logs btc-watcher-backend

# 检查端口
netstat -tuln | grep 8000
# 或
ss -tuln | grep 8000

# 进入容器调试
docker exec -it btc-watcher-backend /bin/bash
```

### 问题3: 数据库连接失败

```bash
# 检查数据库容器
docker logs btc-watcher-db

# 测试数据库连接
docker exec btc-watcher-db pg_isready -U btc_watcher

# 进入数据库
docker exec -it btc-watcher-db psql -U btc_watcher
```

### 问题4: 前端无法访问

```bash
# 检查nginx容器
docker logs btc-watcher-nginx

# 检查前端容器
docker logs btc-watcher-frontend

# 检查nginx配置
docker exec btc-watcher-nginx nginx -t
```

### 问题5: Redis连接失败

```bash
# 检查Redis容器
docker logs btc-watcher-redis

# 测试Redis连接
docker exec btc-watcher-redis redis-cli ping
```

---

## 测试最佳实践

### 1. 测试前清理环境

```bash
# 停止所有容器
docker-compose down

# 清理数据（谨慎！会删除所有数据）
docker-compose down -v

# 重新启动
docker-compose up -d
```

### 2. 监控测试过程

```bash
# 实时查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
```

### 3. 性能测试

```bash
# 使用ab（Apache Bench）进行压力测试
ab -n 1000 -c 10 http://localhost:8000/api/v1/system/health

# 使用wrk进行性能测试
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/system/health
```

### 4. 测试覆盖率

```bash
# 运行测试并生成覆盖率报告
cd backend
pytest tests/ --cov=. --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

---

## 自动化测试

### GitHub Actions（示例）

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v
```

---

## 测试检查清单

启动前验证：
- [ ] Docker已安装并运行
- [ ] Docker Compose已安装
- [ ] 环境配置文件(.env)已创建
- [ ] 必要端口未被占用
- [ ] 项目文件完整

启动后验证：
- [ ] 所有容器正常运行
- [ ] 后端API可访问
- [ ] 前端可访问
- [ ] 数据库连接正常
- [ ] Redis连接正常
- [ ] API文档可访问

功能测试：
- [ ] 用户注册成功
- [ ] 用户登录成功
- [ ] 创建策略成功
- [ ] 启动策略成功
- [ ] 停止策略成功
- [ ] 系统容量查询正常
- [ ] 信号列表查询正常

---

## 联系支持

如果遇到问题：
1. 查看日志: `docker-compose logs`
2. 查看文档: README.md
3. 提交Issue: https://github.com/yourusername/btc-watcher/issues

---

**祝测试顺利！** 🚀
