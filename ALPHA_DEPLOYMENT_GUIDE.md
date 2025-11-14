# BTC Watcher Alpha测试部署指南
# Alpha Testing Deployment Guide

**版本**: v1.0.0
**更新日期**: 2025-10-31
**适用场景**: Alpha测试环境快速部署和更新

---

## 📋 部署概述

本文档提供Alpha测试环境的完整部署流程，包括首次部署、增量更新、故障排查等。

### 架构概览

```
用户浏览器
    ↓ (访问 http://localhost:8501)
Nginx反向代理 (端口8501)
    ├─ /api/* → 后端API (端口8000)
    └─ /* → 前端服务 (端口3000)

后端API (端口8000)
    ├─ PostgreSQL (端口5432)
    ├─ Redis (端口6379)
    └─ FreqTrade实例 (端口8081-9080)
```

---

## 🚀 快速部署

### 方式一：一键启动（推荐）

```bash
cd /home/xd/project/btc-watcher
./start_alpha.sh
```

启动成功后访问: http://localhost:8501

### 方式二：手动启动

参见 [手动部署步骤](#手动部署步骤)

---

## 📦 首次部署

### 前置要求

**系统要求**:
- 操作系统: Linux (Ubuntu 20.04+ / Debian 11+)
- 内存: 最低4GB，推荐8GB+
- 磁盘: 最低20GB可用空间

**软件依赖**:
- Docker 20.10+
- Docker Compose 2.0+ (或 docker-compose 1.29+)
- Python 3.10+
- Node.js 18+ & npm 9+
- Git

### 1. 检查环境

```bash
cd /home/xd/project/btc-watcher
./verify_deployment.sh
```

如果验证失败，请根据提示安装缺失的依赖。

### 2. 配置环境变量

```bash
# 检查.env文件是否存在
ls -la .env

# 如果不存在，从示例复制
cp .env.example .env

# 编辑配置（可选）
nano .env
```

**重要配置���**:
```env
# 数据库
DATABASE_URL=postgresql://btc_watcher_user:btc_watcher_password@localhost:5432/btc_watcher

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-here

# 环境标识
ENVIRONMENT=alpha
```

### 3. 启动数据库服务

```bash
# 启动PostgreSQL和Redis
docker-compose up -d db redis

# 验证启动成功
docker ps | grep -E "postgres|redis"

# 等待数据库就绪
sleep 5
```

### 4. 初始化数据库

```bash
cd backend
source venv/bin/activate

# 运行数据库迁移
alembic upgrade head

# 初始化默认用户（如果需要）
python init_default_user.py

deactivate
cd ..
```

### 5. 启动应用服务

```bash
# 使用一键启动脚本
./start_alpha.sh
```

或手动启动（参见下一节）。

### 6. 验证部署

```bash
# 检查服务状态
./verify_deployment.sh

# 测试健康检查
curl http://localhost:8501/health

# 测试API文档
curl -I http://localhost:8501/docs

# 测试前端（浏览器访问）
# http://localhost:8501
```

**预期结果**:
```json
{
  "status": "healthy",
  "app_name": "BTC Watcher",
  "version": "1.0.0",
  "environment": "alpha"
}
```

---

## 🔄 增量更新部署

当代码有更新时，使用以下流程进行增量部署。

### 场景1: 仅前端代码更新

**适用**: 修改了前端代码（`frontend/src/`）

```bash
cd /home/xd/project/btc-watcher

# 方法1: 使用重启脚本（推荐）
./restart-frontend.sh

# 方法2: 手动重启
pkill -f "vite"
cd frontend
npm run dev &
cd ..

# 验证
sleep 3
curl -I http://localhost:3000
```

**刷新浏览器**: Ctrl + Shift + R (强制刷新)

### 场景2: 仅后端代码更新

**适用**: 修改了后端代码（`backend/api/`, `backend/services/`等）

```bash
cd /home/xd/project/btc-watcher

# 1. 停止后端
pkill -f "uvicorn.*main:app"

# 2. 重启后端
cd backend
source venv/bin/activate
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &
deactivate
cd ..

# 3. 验证
sleep 3
curl http://localhost:8000/health
```

**注意**: 如果后端启动了`--reload`模式，代码变更会自动重载，无需手动重启。

### 场景3: 数据库模型变更

**适用**: 修改了数据库模型（`backend/models/`）

```bash
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate

# 1. 创建迁移文件
alembic revision --autogenerate -m "描述你的变更"

# 2. 查看迁移SQL（可选）
alembic upgrade head --sql

# 3. 执行迁移
alembic upgrade head

# 4. 重启后端（如果没有使用--reload模式）
pkill -f "uvicorn.*main:app"
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &

deactivate
cd ..
```

### 场景4: 依赖包更新

**前端依赖更新** (`package.json`变更):
```bash
cd /home/xd/project/btc-watcher/frontend

# 1. 停止前端
pkill -f "vite"

# 2. 安装新依赖
npm install

# 3. 重启前端
npm run dev &

cd ..
```

**后端依赖更新** (`requirements.txt`变更):
```bash
cd /home/xd/project/btc-watcher/backend

# 1. 激活虚拟环境
source venv/bin/activate

# 2. 安装新依赖
pip install -r requirements.txt

# 3. 重启后端
pkill -f "uvicorn.*main:app"
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &

deactivate
cd ..
```

### 场景5: Nginx配置更新

**适用**: 修改了 `nginx/nginx.conf`

```bash
cd /home/xd/project/btc-watcher

# 1. 验证配置语法
docker run --rm -v $PWD/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine nginx -t

# 2. 重启Nginx容器
docker restart btc-watcher-nginx

# 或完全重建
docker rm -f btc-watcher-nginx
docker run -d --name btc-watcher-nginx \
  --add-host=host.docker.internal:host-gateway \
  -p 8501:8501 \
  -v $PWD/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine

# 3. 验证
curl -I http://localhost:8501/health
```

### 场景6: 完整重启（所有服务）

**适用**: 重大更新或环境异常

```bash
cd /home/xd/project/btc-watcher

# 1. 停止所有服务
./stop_alpha.sh

# 2. （可选）清理日志
rm -f /tmp/backend.log /tmp/frontend.log

# 3. 重新启动
./start_alpha.sh

# 4. 验证
sleep 10
curl http://localhost:8501/health
```

---

## 🛠️ 手动部署步骤

如果一键脚本失败，可以按以下步骤手动部署。

### 1. 启动数据库

```bash
# PostgreSQL
docker start btc-watcher-db-1 || \
docker-compose up -d db

# Redis
docker start btc-watcher-redis-1 || \
docker-compose up -d redis

# 验证
docker ps | grep -E "postgres|redis"
```

### 2. 启动后端API

```bash
cd /home/xd/project/btc-watcher/backend

# 激活虚拟环境
source venv/bin/activate

# 方式1: 前台运行（调试用）
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 方式2: 后台运行（生产用）
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &

# 查看进程
ps aux | grep uvicorn

# 查看日志
tail -f /tmp/backend_new.log

deactivate
```

### 3. 启动前端服务

```bash
cd /home/xd/project/btc-watcher/frontend

# 方式1: 前台运行（调试用）
npm run dev

# 方式2: 后台运行（生产用）
nohup npm run dev > /tmp/frontend.log 2>&1 &

# 查看进程
ps aux | grep vite

# 查看日志
tail -f /tmp/frontend.log
```

### 4. 启动Nginx反向代理

```bash
cd /home/xd/project/btc-watcher

# 删除旧容器（如果存在）
docker rm -f btc-watcher-nginx

# 启动新容器
docker run -d --name btc-watcher-nginx \
  --add-host=host.docker.internal:host-gateway \
  -p 8501:8501 \
  -v $PWD/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine

# 验证
docker ps | grep nginx
docker logs btc-watcher-nginx
```

---

## 🔍 故障排查

### 问题1: 服务无法启动

**症状**: `start_alpha.sh`执行后服务未运行

**排查步骤**:

1. 检查端口占用
```bash
# 检查关键端口
lsof -i :8501  # Nginx
lsof -i :8000  # 后端
lsof -i :3000  # 前端
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 如果端口被占用，杀死进程
kill -9 <PID>
```

2. 检查服务日志
```bash
# 后端日志
tail -100 /tmp/backend_new.log

# 前端日志
tail -100 /tmp/frontend.log

# Nginx日志
docker logs btc-watcher-nginx

# 数据库日志
docker logs btc-watcher-db-1
```

3. 检查Docker服务
```bash
# Docker服务状态
sudo systemctl status docker

# 启动Docker（如果未运行）
sudo systemctl start docker

# 查看容器状态
docker ps -a
```

### 问题2: 后端API 500错误

**症状**: API请求返回500 Internal Server Error

**排查步骤**:

```bash
# 1. 查看后端日志
tail -100 /tmp/backend_new.log | grep -E "ERROR|Exception"

# 2. 测试数据库连接
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate
python -c "from database.session import engine; print('DB OK')"
deactivate

# 3. 检查Redis连接
redis-cli ping
# 应返回: PONG

# 4. 重启后端
pkill -f "uvicorn.*main:app"
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# 观察启动日志
```

### 问题3: 前端无法访问

**症状**: 浏览器无法打开 http://localhost:8501

**排查步骤**:

```bash
# 1. 检查Nginx是否运行
docker ps | grep nginx

# 2. 测试Nginx配置
docker exec btc-watcher-nginx nginx -t

# 3. 检查后端和前端服务
curl http://localhost:8000/health  # 后端
curl -I http://localhost:3000      # 前端

# 4. 查看Nginx日志
docker logs --tail=50 btc-watcher-nginx

# 5. 重启Nginx
docker restart btc-watcher-nginx

# 如果Nginx无法启动，检查配置文件
cat /home/xd/project/btc-watcher/nginx/nginx.conf
```

### 问题4: WebSocket连接失败

**症状**: 前端显示"WebSocket连接失败"或降级到轮询模式

**排查步骤**:

```bash
# 1. 检查Nginx WebSocket配置
cat /home/xd/project/btc-watcher/nginx/nginx.conf | grep -A 5 "map \$http_upgrade"

# 应该包含:
# map $http_upgrade $connection_upgrade {
#     default upgrade;
#     ''      close;
# }

# 2. 测试WebSocket连接（需要安装wscat）
npm install -g wscat
wscat -c "ws://localhost:8501/api/v1/ws?token=YOUR_JWT_TOKEN"

# 3. 查看后端WebSocket日志
tail -f /tmp/backend_new.log | grep -i websocket

# 4. 检查JWT token是否有效
curl -X GET "http://localhost:8501/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 如果token过期，重新登录获取新token
```

### 问题5: 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**排查步骤**:

```bash
# 1. 检查PostgreSQL容器
docker ps | grep postgres

# 2. 测试数据库连接
PGPASSWORD=btc_watcher_password psql -h localhost -U btc_watcher_user -d btc_watcher -c "SELECT 1;"

# 3. 查看PostgreSQL日志
docker logs btc-watcher-db-1 --tail=50

# 4. 重启PostgreSQL
docker restart btc-watcher-db-1

# 5. 检查数据库表是否存在
PGPASSWORD=btc_watcher_password psql -h localhost -U btc_watcher_user -d btc_watcher -c "\dt"

# 如果表不存在，运行迁移
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate
alembic upgrade head
deactivate
```

### 问题6: 前端构建失败或白屏

**症状**: 前端无法启动或页面显示空白

**排查步骤**:

```bash
# 1. 清理node_modules重新安装
cd /home/xd/project/btc-watcher/frontend
rm -rf node_modules package-lock.json
npm install

# 2. 清理Vite缓存
rm -rf .vite node_modules/.vite

# 3. 检查环境变量
cat .env.development
# 确保配置正确

# 4. 手动启动查看错误
npm run dev
# 观察启动日志

# 5. 检查浏览器控制台
# 打开浏览器开发者工具，查看Console和Network标签
```

---

## 📊 服务健康检查

### 快速检查脚本

创建 `check_health.sh`:

```bash
#!/bin/bash

echo "=== BTC Watcher 服务健康检查 ==="
echo ""

# 1. PostgreSQL
if docker ps | grep btc-watcher-db-1 > /dev/null; then
    echo "✅ PostgreSQL: 运行中"
else
    echo "❌ PostgreSQL: 未运行"
fi

# 2. Redis
if docker ps | grep btc-watcher-redis-1 > /dev/null; then
    echo "✅ Redis: 运行中"
else
    echo "❌ Redis: 未运行"
fi

# 3. 后端API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端API: 正常 (端口8000)"
else
    echo "❌ 后端API: 异常"
fi

# 4. 前端服务
if curl -s -I http://localhost:3000 | grep -q "200\|301\|302"; then
    echo "✅ 前端服务: 正常 (端口3000)"
else
    echo "❌ 前端服务: 异常"
fi

# 5. Nginx
if docker ps | grep btc-watcher-nginx > /dev/null; then
    if curl -s http://localhost:8501/health > /dev/null 2>&1; then
        echo "✅ Nginx: 正常 (端口8501)"
    else
        echo "⚠️  Nginx: 运行中但无法访问"
    fi
else
    echo "❌ Nginx: 未运行"
fi

echo ""
echo "=== 检查完成 ==="
```

使用:
```bash
chmod +x check_health.sh
./check_health.sh
```

---

## 🔙 回滚方案

### 代码回滚

```bash
cd /home/xd/project/btc-watcher

# 1. 查看Git历史
git log --oneline -10

# 2. 回滚到指定commit
git reset --hard <commit-hash>

# 3. 重新部署
./stop_alpha.sh
./start_alpha.sh
```

### 数据库回滚

```bash
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate

# 1. 查看迁移历史
alembic history

# 2. 回滚到指定版本
alembic downgrade <revision>

# 或回滚一个版本
alembic downgrade -1

# 3. 重启后端
deactivate
pkill -f "uvicorn.*main:app"
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &
deactivate
```

---

## 📝 部署检查清单

### 首次部署前

- [ ] 系统满足最低要求（4GB内存，20GB磁盘）
- [ ] Docker和Docker Compose已安装
- [ ] Python 3.10+和pip已安装
- [ ] Node.js 18+和npm已安装
- [ ] 端口8501, 8000, 3000, 5432, 6379未被占用
- [ ] `.env`文件已配置
- [ ] 数据库已初始化

### 每次部署后

- [ ] 所有服务进程正常运行
- [ ] 健康检查返回200 OK
- [ ] API文档可访问 (http://localhost:8501/docs)
- [ ] 前端页面可访问 (http://localhost:8501)
- [ ] WebSocket连接正常（如适用）
- [ ] 测试账号可以登录
- [ ] 关键功能测试通过

### 生产部署前（Beta/正式）

- [ ] 所有Alpha测试Bug已修复
- [ ] 性能测试通过
- [ ] 安全审计完成
- [ ] 数据备份方案就绪
- [ ] 监控告警配置完成
- [ ] SSL证书已配置
- [ ] 防火墙规则已设置

---

## 🚨 紧急处理

### 系统完全崩溃

```bash
# 1. 停止所有服务
./stop_alpha.sh

# 2. 清理残留进程
pkill -f "uvicorn"
pkill -f "vite"
docker stop btc-watcher-nginx btc-watcher-db-1 btc-watcher-redis-1

# 3. 清理Docker资源（谨慎）
docker system prune -f

# 4. 检查磁盘空间
df -h

# 5. 检查内存
free -h

# 6. 重新启动
./start_alpha.sh
```

### 数据库损坏

```bash
# 1. 停止后端
pkill -f "uvicorn.*main:app"

# 2. 备份当前数据
docker exec btc-watcher-db-1 pg_dump -U btc_watcher_user btc_watcher > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql

# 3. 重置数据库（警告：会删除所有数据）
docker exec btc-watcher-db-1 psql -U btc_watcher_user -c "DROP DATABASE btc_watcher;"
docker exec btc-watcher-db-1 psql -U btc_watcher_user -c "CREATE DATABASE btc_watcher;"

# 4. 重新运行迁移
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate
alembic upgrade head
python init_default_user.py
deactivate

# 5. 重启后端
cd /home/xd/project/btc-watcher/backend
source venv/bin/activate
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &
deactivate
```

---

## 📞 支持和联系

### 获取帮助

- **文档**: 参见 [ALPHA_TEST_GUIDE.md](ALPHA_TEST_GUIDE.md)
- **API文档**: http://localhost:8501/docs
- **问题反馈**: [在此提交Issue]

### 日志位置

```
后端日志: /tmp/backend_new.log
前端日志: /tmp/frontend.log
Nginx日志: docker logs btc-watcher-nginx
PostgreSQL日志: docker logs btc-watcher-db-1
Redis日志: docker logs btc-watcher-redis-1
```

---

## 📚 相关文档

- [Alpha测试指南](ALPHA_TEST_GUIDE.md) - 测试流程和功能说明
- [实时数据降级实现报告](REALTIME_FALLBACK_IMPLEMENTATION.md) - WebSocket/轮询实现
- [性能优化报告](PERFORMANCE_OPTIMIZATION_REPORT.md) - 性能指标
- [Alpha就绪度评估](ALPHA_READINESS_ASSESSMENT.md) - 系统就绪状态

---

**文档版本**: v1.0.0
**最后更新**: 2025-10-31
**维护者**: BTC Watcher开发团队
