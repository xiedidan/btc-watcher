# Alpha测试部署快速索引

## 📚 可用部署脚本

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| `start_alpha.sh` | 一键启动所有服务 | 首次部署、完整重启 |
| `stop_alpha.sh` | 停止所有服务 | 关闭系统、完整重启前 |
| `check_health.sh` | 健康检查 | 验证服务状态 |
| `deploy_frontend.sh` | 前端更新部署 | 前端代码变更后 |
| `deploy_backend.sh` | 后端更新部署 | 后端代码变更后 |
| `restart-frontend.sh` | 快速重启前端 | 前端简单重启 |
| `verify_deployment.sh` | 部署环境验证 | 首次部署前检查 |

## 🚀 常见部署场景

### 1. 首次部署

```bash
# 1. 验证环境
./verify_deployment.sh

# 2. 启动所有服务
./start_alpha.sh

# 3. 验证状态
./check_health.sh
```

访问: http://localhost:8501

---

### 2. 前端代码更新后

**场景**: 修改了 `frontend/src/` 下的文件

```bash
# 方法1: 完整部署（推荐，支持依赖更新）
./deploy_frontend.sh

# 方法2: 快速重启（仅重启服务）
./restart-frontend.sh
```

**浏览器刷新**: `Ctrl + Shift + R` (强制刷新缓存)

---

### 3. 后端代码更新后

**场景**: 修改了 `backend/` 下的文件

```bash
# 完整部署（支持依赖更新和数据库迁移）
./deploy_backend.sh
```

**注意**: 如果后端启动了 `--reload` 模式，代码变更会自动重载

---

### 4. 数据库模型变更

**场景**: 修改了 `backend/models/` 下的模型

```bash
cd backend
source venv/bin/activate

# 1. 创建迁移
alembic revision --autogenerate -m "描述变更"

# 2. 执行迁移
alembic upgrade head

deactivate
cd ..

# 3. 重启后端（如需要）
./deploy_backend.sh
```

---

### 5. Nginx配置更新

**场景**: 修改了 `nginx/nginx.conf`

```bash
# 重启Nginx容器
docker restart btc-watcher-nginx

# 或完全重建
docker rm -f btc-watcher-nginx
./start_alpha.sh
```

---

### 6. 完整重启

**场景**: 重大更新、环境异常

```bash
# 1. 停止所有服务
./stop_alpha.sh

# 2. 重新启动
./start_alpha.sh

# 3. 验证状态
./check_health.sh
```

---

## 🔍 故障排查

### 检查服务状态

```bash
./check_health.sh
```

### 查看日志

```bash
# 后端日志
tail -f /tmp/backend_new.log

# 前端日志
tail -f /tmp/frontend.log

# Nginx日志
docker logs btc-watcher-nginx

# 数据库日志
docker logs btc-watcher-db-1
```

### 检查端口占用

```bash
# 检查关键端口
lsof -i :8501  # Nginx
lsof -i :8000  # 后端
lsof -i :3000  # 前端
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
```

### 清理残留进程

```bash
# 前端
pkill -f "vite"

# 后端
pkill -f "uvicorn.*main:app"

# Docker容器
docker stop btc-watcher-nginx btc-watcher-db-1 btc-watcher-redis-1
```

---

## 📝 部署前检查清单

### 首次部署

- [ ] Docker和Docker Compose已安装
- [ ] Python 3.10+已安装
- [ ] Node.js 18+已安装
- [ ] 端口8501、8000、3000、5432、6379未被占用
- [ ] `.env`文件已配置
- [ ] 运行 `./verify_deployment.sh` 通过

### 每次部署后

- [ ] 运行 `./check_health.sh` 全部通过
- [ ] 访问 http://localhost:8501 正常
- [ ] API文档可访问 http://localhost:8501/docs
- [ ] 测试账号可以登录 (alpha1 / Alpha@2025)

---

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 主应用 | http://localhost:8501 | 通过Nginx访问 |
| API文档 | http://localhost:8501/docs | Swagger UI |
| 健康检查 | http://localhost:8501/health | 服务状态 |
| 后端直接访问 | http://localhost:8000 | 调试用 |
| 前端直接访问 | http://localhost:3000 | 调试用 |

---

## 📚 详细文档

- **[Alpha部署指南](ALPHA_DEPLOYMENT_GUIDE.md)** - 完整的部署流程和故障排查
- **[Alpha测试指南](ALPHA_TEST_GUIDE.md)** - 测试流程和功能说明
- **[实时数据降级实现](REALTIME_FALLBACK_IMPLEMENTATION.md)** - WebSocket/轮询实现

---

## 🆘 获取帮助

**遇到问题？**

1. 运行 `./check_health.sh` 检查服务状态
2. 查看对应的日志文件
3. 参考 [ALPHA_DEPLOYMENT_GUIDE.md](ALPHA_DEPLOYMENT_GUIDE.md) 的故障排查部分
4. 如果问题持续，提交Issue并附上日志信息

---

**最后更新**: 2025-10-31
