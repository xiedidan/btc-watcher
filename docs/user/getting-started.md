# BTC Watcher 快速开始指南

## 🚀 5分钟上手指南

BTC Watcher 是一个专业的加密货币信号监控和分析系统，支持999个并发FreqTrade策略实例。本指南将帮助您快速启动和运行系统。

## 📋 前置要求

### 系统要求
- **操作系统**: Linux (推荐 Ubuntu 20.04+) / macOS / Windows WSL2
- **内存**: 最少4GB (推荐8GB+)
- **存储**: 最少10GB可用空间
- **网络**: 稳定的互联网连接

### 软件依赖
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 任意版本

## 🔧 环境检查

在开始之前，请验证您的环境是否满足要求：

```bash
# 检查Docker版本
docker --version

# 检查Docker Compose版本
docker compose version

# 检查可用内存
free -h  # Linux
# 或
system_profiler SPHardwareDataType | grep "Memory:"  # macOS
```

## 📥 安装步骤

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/btc-watcher.git
cd btc-watcher
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑配置文件
nano backend/.env  # 或使用您喜欢的编辑器
```

**关键配置项**:
```bash
# 数据库配置
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://btc_watcher:your_secure_password@db:5432/btc_watcher

# JWT密钥 (必须修改)
SECRET_KEY=your-very-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# 通知配置 (可选)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. 验证部署环境
```bash
# 运行部署前验证
./scripts/diagnostics/verify_deployment.sh
```

### 4. 启动系统
```bash
# 使用Docker Compose启动所有服务
docker-compose up -d

# 或使用Makefile快捷命令
make up
```

### 5. 验证运行状态
```bash
# 检查容器状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 运行运行时验证
./scripts/diagnostics/verify_runtime.sh
```

## 🌐 访问系统

系统启动后，您可以通过以下地址访问：

- **前端界面**: http://localhost
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/api/v1/system/health

## 👤 创建第一个用户

### 通过API创建用户
```bash
# 注册用户
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "your_password"
  }'

# 用户登录
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=admin&password=your_password'
```

### 通过前端界面
1. 打开 http://localhost
2. 点击"注册"按钮
3. 填写注册信息
4. 登录系统

## 🎯 快速体验

### 1. 查看系统状态
登录后，您将看到仪表盘显示：
- 系统容量使用情况
- 运行中的策略数量
- 最新信号统计
- 容量趋势图表

### 2. 创建测试策略
```bash
# 创建策略 (需要JWT令牌)
curl -X POST "http://localhost:8000/api/v1/strategies/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试策略",
    "strategy_class": "TestStrategy",
    "exchange": "binance",
    "timeframe": "1h",
    "config": {
      "stake_amount": 10,
      "max_open_trades": 3
    }
  }'
```

### 3. 启动策略
```bash
# 启动策略 (替换{strategy_id})
curl -X POST "http://localhost:8000/api/v1/strategies/{strategy_id}/start" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 系统监控

### 实时监控
- **系统指标**: CPU、内存、磁盘使用率
- **策略状态**: 运行、停止、错误状态
- **容量使用**: 已用/可用策略槽位
- **信号统计**: 实时信号接收情况

### 通知设置
系统支持多种通知渠道：
- Telegram Bot
- 企业微信
- 飞书
- 邮件

## 🔧 常用命令

### 系统管理
```bash
# 启动系统
make up

# 停止系统
make down

# 重启系统
make restart

# 查看状态
make ps

# 查看日志
make logs
```

### 数据管理
```bash
# 备份数据库
make db-backup

# 清理容器
make clean

# 重建容器
make rebuild
```

### 测试验证
```bash
# 运行API测试
make test

# 验证部署
make test-verify

# 冒烟测试
make smoke
```

## 🚨 常见问题

### 端口冲突
如果端口被占用，请检查：
```bash
# 检查端口占用
netstat -tulpn | grep -E ':80|:8000|:5432|:6379'

# 修改端口映射
nano docker-compose.yml
```

### 内存不足
如果系统内存不足：
1. 减少并发策略数量
2. 增加Docker内存限制
3. 升级硬件配置

### 数据库连接失败
```bash
# 检查数据库容器
docker-compose logs db

# 重置数据库
docker-compose down -v
docker-compose up -d
```

## 📚 下一步

完成快速开始后，您可以：
- 📖 阅读[完整部署指南](deployment-guide.md)
- 🔧 查看[用户手册](user-guide.md)
- 🛠️ 学习[开发指南](../development/)
- 📊 了解[系统架构](../architecture/system-design.md)

## 🆘 获取帮助

如果遇到问题：
1. 查看[故障排查指南](troubleshooting.md)
2. 检查[FAQ](faq.md)
3. 查看系统日志：`make logs`
4. 提交Issue到项目仓库

---

**⏱️ 预计时间**: 5-10分钟
**📈 难度**: 初级
**🎯 目标**: 运行基本系统

**下一步**: [部署指南](deployment-guide.md) →