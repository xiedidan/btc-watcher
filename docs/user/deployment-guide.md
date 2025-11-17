# BTC Watcher 部署指南

## 🎯 概述

本指南提供BTC Watcher的完整部署流程，包括开发环境、测试环境和生产环境的部署方案。

## 📋 部署前准备

### 1. 系统要求

#### 最低配置（开发环境）
- **CPU**: 2核
- **内存**: 4GB
- **存储**: 20GB SSD
- **网络**: 1Mbps带宽

#### 推荐配置（生产环境）
- **CPU**: 8核+
- **内存**: 16GB+
- **存储**: 100GB+ SSD
- **网络**: 10Mbps+带宽

### 2. 软件依赖

```bash
# 检查Docker版本
docker --version  # 需要 20.10+

# 检查Docker Compose版本
docker compose version  # 需要 2.0+

# 检查Git
git --version
```

### 3. 网络要求

| 服务 | 端口 | 说明 | 防火墙 |
|------|------|------|--------|
| Web界面 | 80/443 | HTTP/HTTPS | 必需开放 |
| API服务 | 8000 | FastAPI后端 | 内网访问 |
| 数据库 | 5432 | PostgreSQL | 内网访问 |
| 缓存 | 6379 | Redis | 内网访问 |
| 策略实例 | 8081-9080 | FreqTrade | 内网访问 |

## 🔧 环境配置

### 1. 获取代码

```bash
# 克隆仓库
git clone https://github.com/yourusername/btc-watcher.git
cd btc-watcher

# 切换到稳定版本
git checkout v1.0.0
```

### 2. 环境变量配置

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑配置文件
nano backend/.env
```

#### 关键配置说明

```bash
# === 数据库配置 ===
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://btc_watcher:your_secure_password_here@db:5432/btc_watcher

# === 安全密钥 ===
# ⚠️ 重要：生产环境必须修改这些密钥
SECRET_KEY=your-very-secure-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# === FreqTrade配置 ===
MAX_CONCURRENT_STRATEGIES=999
FREQTRADE_BASE_PORT=8081
FREQTRADE_MAX_PORT=9080

# === Redis配置 ===
REDIS_PASSWORD=your_redis_password_here

# === 通知配置 ===
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 邮件
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 企业微信
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key

# 飞书
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_token
```

### 3. 安全加固

#### 生成安全密钥
```bash
# 生成强密码
openssl rand -base64 32

# 生成JWT密钥
openssl rand -hex 32
```

#### 文件权限
```bash
# 设置敏感文件权限
chmod 600 backend/.env
chmod 700 scripts/
```

## 🚀 部署方式

### 方式一：Docker Compose部署（推荐）

#### 标准部署
```bash
# 1. 验证部署环境
./scripts/diagnostics/verify_deployment.sh

# 2. 启动所有服务
docker-compose up -d

# 3. 验证运行状态
./scripts/diagnostics/verify_runtime.sh

# 4. 查看服务状态
docker-compose ps
```

#### 生产环境部署
```bash
# 使用生产配置
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 或者使用环境变量
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker-compose up -d
```

### 方式二：分步部署

#### 1. 部署基础设施
```bash
# 启动数据库和缓存
docker-compose up -d db redis

# 等待数据库就绪
sleep 30

# 验证数据库连接
docker-compose exec db pg_isready -U btc_watcher
```

#### 2. 部署后端服务
```bash
# 启动后端服务
docker-compose up -d backend

# 验证后端健康状态
curl -f http://localhost:8000/api/v1/system/health || echo "Backend not ready"
```

#### 3. 部署前端服务
```bash
# 启动前端服务
docker-compose up -d frontend nginx

# 验证前端访问
curl -f http://localhost || echo "Frontend not ready"
```

### 方式三：Kubernetes部署

#### 创建命名空间
```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: btc-watcher
```

#### 配置ConfigMap
```yaml
# kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: btc-watcher-config
  namespace: btc-watcher
data:
  .env: |
    DATABASE_URL=postgresql://btc_watcher:password@postgres:5432/btc_watcher
    REDIS_URL=redis://redis:6379/0
    SECRET_KEY=your-secret-key
```

#### 部署应用
```bash
# 应用配置
kubectl apply -f kubernetes/

# 查看部署状态
kubectl get pods -n btc-watcher

# 查看服务
kubectl get svc -n btc-watcher
```

## 🔍 部署验证

### 1. 健康检查
```bash
# 系统健康检查
curl http://localhost:8000/api/v1/system/health

# 容量检查
curl http://localhost:8000/api/v1/system/capacity

# 数据库连接检查
curl http://localhost:8000/api/v1/system/info
```

### 2. 功能验证
```bash
# 创建测试用户
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com", "password": "test123"}'

# 用户登录
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=test&password=test123'
```

### 3. 监控验证
```bash
# 检查容器状态
docker-compose ps

# 查看资源使用
docker stats

# 检查日志
docker-compose logs --tail=50
```

## 🛡️ 安全部署

### 1. SSL证书配置

#### 使用Let's Encrypt
```bash
# 安装certbot
sudo apt install certbot

# 获取证书
sudo certbot certonly --standalone -d your-domain.com

# 更新Nginx配置
sudo nano nginx/nginx.conf
```

#### Nginx SSL配置
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 防火墙配置

#### UFW防火墙（Ubuntu）
```bash
# 启用防火墙
sudo ufw enable

# 允许SSH
sudo ufw allow 22/tcp

# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 拒绝其他端口
sudo ufw deny 8000/tcp
sudo ufw deny 5432/tcp
sudo ufw deny 6379/tcp
```

#### iptables规则
```bash
# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许回环接口
iptables -A INPUT -i lo -j ACCEPT

# 允许SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 拒绝数据库端口（仅内网访问）
iptables -A INPUT -p tcp --dport 5432 -j DROP
iptables -A INPUT -p tcp --dport 6379 -j DROP
```

### 3. 数据库安全

#### PostgreSQL配置
```sql
-- 创建专用用户
CREATE USER btc_watcher WITH PASSWORD 'secure_password';

-- 创建数据库
CREATE DATABASE btc_watcher OWNER btc_watcher;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE btc_watcher TO btc_watcher;

-- 撤销公共权限
REVOKE ALL ON DATABASE btc_watcher FROM PUBLIC;
```

#### 连接限制
```bash
# 编辑postgresql.conf
nano postgres/postgresql.conf

# 添加配置
listen_addresses = 'localhost'
max_connections = 100
ssl = on
```

## 📊 性能优化

### 1. 数据库优化

#### 连接池配置
```python
# backend/database/session.py
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
```

#### 索引优化
```sql
-- 策略查询优化
CREATE INDEX idx_strategies_user_status ON strategies(user_id, status);
CREATE INDEX idx_strategies_port ON strategies(port);

-- 信号查询优化
CREATE INDEX idx_signals_strategy_timestamp ON signals(strategy_id, timestamp DESC);
CREATE INDEX idx_signals_strength ON signals(signal_strength);

-- 通知查询优化
CREATE INDEX idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

### 2. Redis优化

#### 缓存策略
```python
# backend/core/cache.py
CACHE_CONFIG = {
    "default_ttl": 300,  # 5分钟
    "system_ttl": 60,    # 1分钟
    "user_ttl": 1800,    # 30分钟
}
```

#### 内存配置
```bash
# redis/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 60 1000
```

### 3. 应用优化

#### 异步配置
```python
# backend/main.py
APP_CONFIG = {
    "workers": 4,
    "backlog": 2048,
    "keepalive": 5,
    "timeout": 30,
}
```

#### Gunicorn配置
```python
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 1000
max_requests_jitter = 50
```

## 🔧 运维管理

### 1. 备份策略

#### 数据库备份
```bash
# 自动备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/postgres"

# 创建备份
docker-compose exec -T db pg_dump -U btc_watcher btc_watcher > "$BACKUP_DIR/backup_$DATE.sql"

# 压缩备份
gzip "$BACKUP_DIR/backup_$DATE.sql"

# 删除旧备份（保留7天）
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete
```

#### 应用备份
```bash
# 备份上传的策略文件
tar -czf "strategies_backup_$DATE.tar.gz" data/strategies/

# 备份配置文件
cp docker-compose.yml "docker-compose_backup_$DATE.yml"
cp backend/.env "env_backup_$DATE"
```

### 2. 监控告警

#### 系统监控
```bash
# 监控脚本
#!/bin/bash
# 检查磁盘空间
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "磁盘使用率过高: ${DISK_USAGE}%"
    # 发送告警
fi

# 检查内存使用
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    echo "内存使用率过高: ${MEMORY_USAGE}%"
    # 发送告警
fi
```

#### 应用监控
```bash
# 健康检查脚本
#!/bin/bash
HEALTH_URL="http://localhost:8000/api/v1/system/health"

if ! curl -f "$HEALTH_URL" > /dev/null 2>&1; then
    echo "系统健康检查失败"
    # 重启服务或发送告警
fi
```

### 3. 日志管理

#### 日志轮转
```bash
# /etc/logrotate.d/btc-watcher
/var/log/btc-watcher/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
```

#### 日志收集
```bash
# 使用ELK Stack收集日志
docker-compose -f docker-compose.logging.yml up -d
```

## 🚨 故障排查

### 常见问题

#### 1. 容器启动失败
```bash
# 查看容器日志
docker-compose logs [service-name]

# 检查配置文件
docker-compose config

# 重新构建容器
docker-compose build --no-cache
```

#### 2. 数据库连接失败
```bash
# 检查数据库容器
docker-compose exec db pg_isready -U btc_watcher

# 检查网络连接
docker-compose exec backend nc -z db 5432

# 重置数据库
docker-compose down -v
docker-compose up -d db
```

#### 3. 性能问题
```bash
# 检查资源使用
docker stats

# 检查慢查询
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "SELECT * FROM pg_stat_activity;"

# 优化配置
./scripts/diagnostics/check_health.sh
```

## 📈 扩展部署

### 1. 水平扩展

#### 负载均衡
```nginx
# nginx负载均衡配置
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

#### 数据库读写分离
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: btc_watcher
      POSTGRES_USER: btc_watcher
      POSTGRES_PASSWORD: password
      POSTGRES_PRIMARY: 'true'
  
  postgres-replica:
    image: postgres:15
    environment:
      POSTGRES_DB: btc_watcher
      POSTGRES_USER: btc_watcher
      POSTGRES_PASSWORD: password
      POSTGRES_REPLICA: 'true'
```

### 2. 高可用部署

#### 主备模式
```bash
# 使用Keepalived实现VIP
sudo apt install keepalived

# 配置主备切换
nano /etc/keepalived/keepalived.conf
```

#### 集群部署
```bash
# 使用Docker Swarm
docker swarm init
docker stack deploy -c docker-compose.yml btc-watcher

# 使用Kubernetes
kubectl create deployment btc-watcher --image=btc-watcher:latest
kubectl expose deployment btc-watcher --type=LoadBalancer --port=80
```

## 📚 相关文档

- [用户手册](user-guide.md) - 详细使用说明
- [故障排查](troubleshooting.md) - 常见问题解决
- [API参考](api-reference.md) - API接口文档
- [运维指南](../operations/) - 运维管理
- [监控配置](../operations/monitoring.md) - 监控设置

---

**⏱️ 预计时间**: 30-60分钟
**📈 难度**: 中级
**🎯 目标**: 生产环境部署

**上一步**: [快速开始](getting-started.md)
**下一步**: [用户手册](user-guide.md) →