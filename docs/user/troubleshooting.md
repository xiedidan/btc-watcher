# BTC Watcher 故障排查指南

## 🎯 概述

本指南帮助用户诊断和解决BTC Watcher系统运行过程中遇到的常见问题。按照问题分类和解决方案的优先级进行组织。

## 🚨 紧急问题（需要立即处理）

### 1. 系统完全无法访问

#### 症状
- ❌ 网页无法打开
- ❌ API无响应
- ❌ Docker容器全部停止

#### 诊断步骤
```bash
# 1. 检查容器状态
docker-compose ps

# 2. 检查系统资源
df -h  # 磁盘空间
free -h  # 内存使用

# 3. 检查端口占用
netstat -tulpn | grep -E ':80|:8000'

# 4. 查看错误日志
docker-compose logs --tail=100
```

#### 解决方案
```bash
# 1. 重启所有服务
docker-compose down
docker-compose up -d

# 2. 如果磁盘满了
# 清理Docker日志
docker system prune -a

# 清理大文件
find / -type f -size +100M -exec ls -lh {} \;

# 3. 如果内存不足
# 停止不必要的服务
systemctl stop non-essential-services

# 增加swap空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 2. 数据库连接失败

#### 症状
- ❌ 错误信息："Database connection failed"
- ❌ 无法登录系统
- ❌ 策略数据无法加载

#### 诊断步骤
```bash
# 1. 检查数据库容器
docker-compose exec db pg_isready -U btc_watcher

# 2. 检查数据库日志
docker-compose logs db

# 3. 检查连接字符串
cat backend/.env | grep DATABASE_URL

# 4. 测试网络连接
docker-compose exec backend nc -z db 5432
```

#### 解决方案
```bash
# 1. 重启数据库
docker-compose restart db

# 2. 如果数据库损坏
# 备份现有数据
docker-compose exec db pg_dump -U btc_watcher btc_watcher > backup.sql

# 重新初始化数据库
docker-compose down -v
docker-compose up -d db

# 恢复数据（如果有备份）
docker-compose exec -T db psql -U btc_watcher -d btc_watcher < backup.sql

# 3. 检查权限
# 进入数据库容器
docker-compose exec db psql -U postgres

# 执行SQL
\l  # 列出数据库
\du  # 列出用户
```

### 3. Redis连接失败

#### 症状
- ❌ 错误信息："Redis connection failed"
- ❌ 缓存功能异常
- ❌ 实时数据推送中断

#### 诊断步骤
```bash
# 1. 检查Redis容器
docker-compose exec redis redis-cli ping

# 2. 检查Redis日志
docker-compose logs redis

# 3. 检查内存使用
docker stats redis
```

#### 解决方案
```bash
# 1. 重启Redis
docker-compose restart redis

# 2. 如果内存不足
# 清理Redis数据
docker-compose exec redis redis-cli FLUSHALL

# 3. 检查配置文件
cat redis/redis.conf | grep maxmemory
```

## ⚠️ 重要问题（影响核心功能）

### 4. 策略无法启动

#### 症状
- ❌ 策略状态显示"error"
- ❌ 启动按钮无响应
- ❌ 端口分配失败

#### 诊断步骤
```bash
# 1. 检查策略日志
docker-compose logs backend | grep -A 10 "strategy_id"

# 2. 检查端口占用
netstat -tulpn | grep 8081  # 替换为具体端口

# 3. 检查系统容量
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/system/capacity

# 4. 检查策略配置
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/strategies/1
```

#### 解决方案
```bash
# 1. 释放被占用的端口
# 查找占用进程
sudo lsof -i :8081

# 终止进程
sudo kill -9 PID

# 2. 如果容量已满
# 停止一些不重要的策略
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/strategies/2/stop

# 3. 检查配置文件
# 验证策略配置格式
cat backend/freqtrade_configs/config_1.json | python -m json.tool

# 4. 重启FreqTrade网关
docker-compose restart backend
```

### 5. 信号接收失败

#### 症状
- ❌ 没有新的交易信号
- ❌ FreqTrade Webhook报错
- ❌ 信号历史记录停止更新

#### 诊断步骤
```bash
# 1. 检查Webhook配置
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/strategies/1

# 2. 测试Webhook
curl -X POST -H "Content-Type: application/json" \
  -d '{"pair":"BTC/USDT","action":"buy","signal_strength":0.8}' \
  http://localhost:8000/api/v1/signals/webhook/1

# 3. 检查网络连通性
# 从FreqTrade容器ping后端
docker exec -it freqtrade_instance_1 ping backend

# 4. 查看信号接收日志
docker-compose logs backend | grep -i "webhook"
```

#### 解决方案
```bash
# 1. 检查Webhook URL格式
# 正确的格式应该是：
# http://backend:8000/api/v1/signals/webhook/{strategy_id}

# 2. 检查防火墙设置
# 确保容器间网络通信正常
sudo iptables -L -n | grep DOCKER

# 3. 重启相关策略
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/strategies/1/stop
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/strategies/1/start

# 4. 检查端口映射
docker-compose ps
```

### 6. WebSocket连接失败

#### 症状
- ❌ 实时数据不更新
- ❌ WebSocket连接断开
- ❌ 前端显示连接错误

#### 诊断步骤
```bash
# 1. 检查WebSocket端口
netstat -tulpn | grep :8000

# 2. 检查Nginx配置
cat nginx/nginx.conf | grep -A 10 websocket

# 3. 测试WebSocket连接
# 使用wscat工具
npm install -g wscat
wscat -c ws://localhost:8000/ws

# 4. 查看WebSocket日志
docker-compose logs backend | grep -i websocket
```

#### 解决方案
```bash
# 1. 检查Nginx代理配置
# 确保nginx.conf包含WebSocket代理设置
location /ws {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}

# 2. 重启Nginx
docker-compose restart nginx

# 3. 检查后端WebSocket配置
# 确保backend/main.py中WebSocket配置正确

# 4. 如果使用FRP，检查配置
cat frp/frpc.ini | grep websocket
```

## ⚙️ 一般问题（功能异常）

### 7. 性能缓慢

#### 症状
- 🐌 页面加载缓慢
- 🐌 API响应时间过长
- 🐌 数据库查询慢

#### 诊断步骤
```bash
# 1. 检查系统资源
top -p $(docker-compose ps -q)

# 2. 检查数据库性能
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "SELECT * FROM pg_stat_activity;"

# 3. 检查API响应时间
curl -w "@curl-format.txt" -o /dev/null http://localhost:8000/api/v1/system/health

# 4. 检查慢查询日志
docker-compose logs db | grep -i "duration"
```

#### 解决方案
```bash
# 1. 数据库优化
# 添加索引
docker-compose exec db psql -U btc_watcher -d btc_watcher << EOF
CREATE INDEX CONCURRENTLY idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX CONCURRENTLY idx_strategies_status ON strategies(status);
EOF

# 2. 增加缓存
# 检查Redis命中率
docker-compose exec redis redis-cli info stats | grep keyspace

# 3. 调整连接池
# 修改backend/database/session.py
DATABASE_CONFIG = {
    "pool_size": 50,  # 增加连接池大小
    "max_overflow": 100,
    "pool_pre_ping": True,
}

# 4. 启用查询缓存
# 在PostgreSQL配置中启用shared_preload_libraries = 'pg_stat_statements'
```

### 8. 内存泄漏

#### 症状
- 📈 内存使用持续增长
- 🔄 需要定期重启服务
- 💥 内存溢出错误

#### 诊断步骤
```bash
# 1. 监控内存使用
docker stats --no-stream

# 2. 检查Python内存使用
# 安装memory_profiler
pip install memory-profiler

# 3. 生成内存快照
# 在代码中添加内存监控
import psutil
import gc

process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
gc.collect()
```

#### 解决方案
```bash
# 1. 重启服务
docker-compose restart backend

# 2. 优化代码
# 检查是否有循环引用
# 确保正确关闭数据库连接
# 及时释放大对象

# 3. 增加内存限制
# 在docker-compose.yml中添加
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M

# 4. 设置自动重启
# 添加健康检查
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/system/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 9. 磁盘空间不足

#### 症状
- 🚨 "No space left on device"错误
- 📝 日志文件过大
- 💾 数据库无法写入

#### 诊断步骤
```bash
# 1. 检查磁盘使用
df -h

# 2. 查找大文件
find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null

# 3. 检查Docker占用
docker system df

# 4. 检查日志大小
du -sh logs/ data/logs/
```

#### 解决方案
```bash
# 1. 清理Docker
# 清理未使用的容器、镜像、网络
docker system prune -a

# 2. 清理日志
# 设置日志轮转
echo "/var/log/btc-watcher/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}" > /etc/logrotate.d/btc-watcher

# 3. 清理数据库日志
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "SELECT pg_size_pretty(pg_database_size('btc_watcher'));"

# 4. 移动数据到外部存储
# 修改docker-compose.yml中的volume挂载
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/external/postgres
```

## 🔧 配置问题

### 10. 环境变量配置错误

#### 症状
- ⚠️ 服务启动失败
- ⚠️ 配置项不生效
- ⚠️ 连接字符串错误

#### 诊断步骤
```bash
# 1. 检查环境变量
cat backend/.env

# 2. 检查变量是否加载
docker-compose exec backend env | grep -E "DATABASE|REDIS|SECRET"

# 3. 验证配置语法
python -c "
import os
from dotenv import load_dotenv
load_dotenv('backend/.env')
print('DATABASE_URL:', os.getenv('DATABASE_URL'))
"
```

#### 解决方案
```bash
# 1. 重新创建环境文件
cp backend/.env.example backend/.env

# 2. 检查特殊字符
# 确保密码中不包含特殊字符
# 或者使用引号包围

# 3. 验证数据库连接
# 使用psql测试连接
psql $DATABASE_URL -c "SELECT 1;"

# 4. 检查文件权限
chmod 600 backend/.env
```

### 11. 时区设置问题

#### 症状
- ⏰ 时间显示不正确
- 📊 数据统计时间错乱
- 🕐 定时任务不执行

#### 诊断步骤
```bash
# 1. 检查系统时区
timedatectl

# 2. 检查容器时区
docker-compose exec backend date

# 3. 检查数据库时区
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "SHOW timezone;"

# 4. 检查应用日志时间戳
docker-compose logs backend | head -10
```

#### 解决方案
```bash
# 1. 设置系统时区
sudo timedatectl set-timezone Asia/Shanghai

# 2. 在docker-compose.yml中添加时区设置
environment:
  - TZ=Asia/Shanghai
  - PGTZ=Asia/Shanghai

# 3. 在PostgreSQL配置中添加
# postgresql.conf
timezone = 'Asia/Shanghai'

# 4. 重启服务
docker-compose restart
```

## 🌐 网络问题

### 12. 容器间网络通信失败

#### 症状
- 🔗 服务间无法访问
- 🚫 网络超时错误
- 💻 容器IP冲突

#### 诊断步骤
```bash
# 1. 检查网络配置
docker network ls
docker network inspect btc-watcher_default

# 2. 测试容器间连通性
docker-compose exec backend ping db
docker-compose exec backend ping redis

# 3. 检查iptables规则
sudo iptables -L -n | grep DOCKER

# 4. 查看网络统计
netstat -i
```

#### 解决方案
```bash
# 1. 重新创建网络
docker-compose down
docker network prune
docker-compose up -d

# 2. 检查防火墙设置
# 临时禁用防火墙测试
sudo ufw disable
# 或添加规则允许容器通信
sudo ufw allow from 172.18.0.0/16

# 3. 检查DNS设置
# 在docker-compose.yml中添加
dns:
  - 8.8.8.8
  - 8.8.4.4

# 4. 使用主机网络模式（测试用）
network_mode: host
```

### 13. 外部API访问失败

#### 症状
- 🌐 无法获取市场数据
- 📡 交易所API连接失败
- 🔗 Webhook发送失败

#### 诊断步骤
```bash
# 1. 测试外部连接
docker-compose exec backend curl -I https://api.binance.com

# 2. 检查DNS解析
docker-compose exec backend nslookup api.binance.com

# 3. 检查代理设置
echo $HTTP_PROXY $HTTPS_PROXY

# 4. 检查证书
openssl s_client -connect api.binance.com:443 -showcerts
```

#### 解决方案
```bash
# 1. 配置DNS
# 在/etc/docker/daemon.json中添加
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}

# 2. 设置代理
# 在docker-compose.yml中添加
environment:
  - HTTP_PROXY=http://proxy.example.com:8080
  - HTTPS_PROXY=http://proxy.example.com:8080
  - NO_PROXY=localhost,127.0.0.1,db,redis

# 3. 更新CA证书
docker-compose exec backend update-ca-certificates

# 4. 检查防火墙出站规则
sudo iptables -L OUTPUT -n -v
```

## 📊 数据问题

### 14. 数据不一致

#### 症状
- 📈 统计数据不准确
- 🔄 数据同步延迟
- ❌ 数据丢失

#### 诊断步骤
```bash
# 1. 检查数据完整性
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "
SELECT 
  (SELECT COUNT(*) FROM strategies) as strategy_count,
  (SELECT COUNT(*) FROM signals) as signal_count,
  (SELECT COUNT(*) FROM notifications) as notification_count;
"

# 2. 检查数据一致性
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "
SELECT s.id, s.name, COUNT(sig.id) as signal_count
FROM strategies s
LEFT JOIN signals sig ON s.id = sig.strategy_id
GROUP BY s.id, s.name
ORDER BY signal_count DESC;
"

# 3. 检查时间戳一致性
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "
SELECT 
  MIN(created_at) as earliest_record,
  MAX(created_at) as latest_record,
  NOW() as current_time
FROM signals;
"
```

#### 解决方案
```bash
# 1. 数据修复脚本
# 创建修复脚本
cat > fix_data.py << 'EOF'
import asyncio
from sqlalchemy import select
from backend.database import get_db
from backend.models import Strategy, Signal

async def fix_data():
    async for db in get_db():
        # 修复孤立信号
        result = await db.execute(
            select(Signal).outerjoin(Strategy)
            .where(Strategy.id.is_(None))
        )
        orphaned_signals = result.scalars().all()
        
        for signal in orphaned_signals:
            await db.delete(signal)
        
        await db.commit()
        print(f"Fixed {len(orphaned_signals)} orphaned signals")

if __name__ == "__main__":
    asyncio.run(fix_data())
EOF

# 2. 重建索引
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "
REINDEX DATABASE btc_watcher;
VACUUM ANALYZE;
"

# 3. 数据备份和验证
./scripts/maintenance/backup.sh
```

### 15. 性能数据不准确

#### 症状
- 📊 响应时间统计异常
- 🔄 监控指标不更新
- 📈 性能报告错误

#### 诊断步骤
```bash
# 1. 检查监控服务状态
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/monitoring/overview

# 2. 检查系统指标
docker-compose exec backend python -c "
import psutil
import time
print(f'CPU: {psutil.cpu_percent()}%')
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'Disk: {psutil.disk_usage(\"/\").percent}%')
"

# 3. 检查监控数据库
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "
SELECT COUNT(*), date_trunc('hour', timestamp) as hour
FROM system_metrics 
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
"
```

#### 解决方案
```bash
# 1. 重启监控服务
docker-compose restart backend

# 2. 清理监控数据
# 保留最近30天的数据
docker-compose exec db psql -U btc_watcher -d btc_watcher -c "
DELETE FROM system_metrics WHERE timestamp < NOW() - INTERVAL '30 days';
DELETE FROM strategy_metrics WHERE timestamp < NOW() - INTERVAL '30 days';
VACUUM ANALYZE;
"

# 3. 重新校准监控
# 手动触发监控更新
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/monitoring/recalculate
```

## 🚀 自动化诊断工具

### 一键诊断脚本
```bash
#!/bin/bash
# 文件名: scripts/diagnostics/full_diagnosis.sh

echo "🔍 BTC Watcher 全面诊断工具"
echo "=================================="

# 检查Docker环境
echo "📦 检查Docker环境..."
docker --version || echo "❌ Docker未安装"
docker compose version || echo "❌ Docker Compose未安装"

# 检查系统资源
echo "💻 检查系统资源..."
echo "磁盘使用:"
df -h | grep -E "(Filesystem|/dev/)"
echo "内存使用:"
free -h

# 检查容器状态
echo "🔍 检查容器状态..."
docker-compose ps

# 检查服务健康
echo "🏥 检查服务健康..."
for service in backend frontend db redis nginx; do
    if docker-compose exec -T $service echo "test" > /dev/null 2>&1; then
        echo "✅ $service 正常运行"
    else
        echo "❌ $service 异常"
    fi
done

# 检查端口
echo "🔌 检查端口..."
for port in 80 8000 5432 6379; do
    if netstat -tulpn | grep -q ":$port "; then
        echo "✅ 端口 $port 已监听"
    else
        echo "❌ 端口 $port 未监听"
    fi
done

# 检查API响应
echo "🌐 检查API响应..."
if curl -f -s http://localhost:8000/api/v1/system/health > /dev/null; then
    echo "✅ API正常响应"
else
    echo "❌ API无响应"
fi

# 检查数据库连接
echo "🗄️ 检查数据库连接..."
if docker-compose exec -T db pg_isready -U btc_watcher > /dev/null 2>&1; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
fi

# 检查Redis连接
echo "💨 检查Redis连接..."
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis连接正常"
else
    echo "❌ Redis连接失败"
fi

echo "=================================="
echo "🔧 诊断完成！如需修复，请查看具体错误项。"
```

### 使用诊断工具
```bash
# 给脚本执行权限
chmod +x scripts/diagnostics/full_diagnosis.sh

# 运行诊断
./scripts/diagnostics/full_diagnosis.sh

# 输出到文件
./scripts/diagnostics/full_diagnosis.sh > diagnosis_report.txt
```

## 📞 获取帮助

### 自助资源
1. **查看日志**: `docker-compose logs --tail=50`
2. **系统状态**: `docker-compose ps`
3. **资源监控**: `docker stats`
4. **健康检查**: `curl http://localhost:8000/api/v1/system/health`

### 社区支持
- 📧 **邮件支持**: support@btc-watcher.com
- 💬 **在线社区**: [Discord服务器](https://discord.gg/btc-watcher)
- 📖 **文档中心**: https://docs.btc-watcher.com
- 🐛 **问题报告**: [GitHub Issues](https://github.com/yourusername/btc-watcher/issues)

### 专业支持
对于企业用户，我们提供：
- 🔧 **7x24技术支持**
- 📞 **电话支持热线**
- 💼 **专属客户经理**
- 🚀 **现场技术支持**

---

**📋 故障报告模板**:

提交问题报告时，请包含以下信息：
1. **问题描述**: 清晰描述遇到的问题
2. **环境信息**: 操作系统、Docker版本、部署方式
3. **错误日志**: 相关的错误日志片段
4. **复现步骤**: 如何重现这个问题
5. **已尝试的解决方案**: 您已经尝试过的解决方法

**相关文档**:
- [部署指南](deployment-guide.md) - 部署配置
- [用户手册](user-guide.md) - 功能使用
- [API参考](api-reference.md) - API接口
- [FAQ](faq.md) - 常见问题答疑

---

**版本**: v1.0.0
**更新日期**: 2025-10-15
**维护团队**: BTC Watcher Support Team