# BTC Watcher - 加密货币监控与通知系统

[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-35495E?style=flat&logo=vue.js&logoColor=4FC08D)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![FreqTrade](https://img.shields.io/badge/FreqTrade-2E3440?style=flat)](https://www.freqtrade.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

**BTC Watcher** 是一个专为个人交易者设计的全方位加密货币监控系统，集成了实时价格监控、技术分析策略、多渠道通知和便捷的Web管理界面。

## ✨ 核心特性

### 📊 Web 管理界面
- **交易对管理**: 多交易所支持，直观管理监控的加密货币交易对
- **策略控制**: 一键启停多个监控策略，实时查看运行状态
- **图表分析**: TradingView级别的K线图，支持多种技术指标叠加
- **信号展示**: 在图表上实时标记策略产生的交易信号
- **数据同步**: Web界面管理远程数据源同步配置

### 📈 价格数据服务 (新增)
- **实时采集**: 多交易所WebSocket实时价格数据收集
- **历史存储**: 高性能时间序列数据库存储，解决API历史数据不准问题
- **数据导出**: RESTful API支持历史数据导出和同步
- **分布式支持**: 支持独立部署价格服务器，远程数据同步

### 🔄 数据同步系统 (新增)
- **增量同步**: 智能增量数据同步，避免重复传输
- **多源支持**: 支持配置多个远程数据源节点
- **状态监控**: 详细的同步状态追踪和Web界面管理
- **容错机制**: 自动重连、失败重试、断点续传

### 🤖 FreqTrade 策略集成
- **多策略支持**: 同时运行多个自定义监控策略
- **信号模式**: 仅输出信号而不执行实际交易，适合主观交易者
- **热配置**: 支持不重启服务修改策略参数
- **回测功能**: 基于真实历史数据验证策略效果

### 📱 多渠道通知系统
- **即时通知**: 微信、飞书、Telegram、邮件、短信多渠道覆盖
- **智能推送**: 支持按策略、货币对、信号类型个性化通知
- **模板定制**: 自定义通知消息格式和内容

### 🐳 一键部署
- **Docker 容器化**: 完全容器化架构，环境隔离
- **跨平台支持**: 支持 WSL2、Linux 等多种环境
- **自动化脚本**: 启动、停止、备份、恢复一键操作
- **灵活部署**: 支持标准部署、价格采集部署、分布式部署等多种模式

## 🚀 快速开始

### 系统要求
- Docker 20.10+
- Docker Compose 2.0+
- 内存: 建议 4GB+ (完整部署建议16GB+)
- 磁盘: 建议 20GB+ (包含历史数据存储)

### 部署选项

#### 选项1: 标准部署（策略监控）
```bash
git clone <repository-url>
cd btc-watcher
cp .env.example .env
# 编辑 .env 文件配置必要环境变量
./scripts/start.sh
```

#### 选项2: 完整部署（包含价格采集）
```bash
# 启动所有服务，包括实时价格采集
./scripts/start.sh --with-price-service
```

#### 选项3: 分布式部署
```bash
# 远程服务器 - 仅价格采集
./scripts/start.sh --price-service-only

# 本地服务器 - 策略监控+数据同步
./scripts/start.sh --with-sync-service
```

### 环境配置说明

核心配置项：

```bash
# 数据库配置
POSTGRES_DB=btc_watcher
POSTGRES_USER=btc_user
POSTGRES_PASSWORD=your_secure_password

# 安全配置
SECRET_KEY=your_jwt_secret_key

# 价格数据服务配置 (新增)
ENABLE_PRICE_SERVICE=true
ENABLE_BINANCE=true
ENABLE_OKX=true
MONITORED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT,DOTUSDT,LINKUSDT

# 数据同步配置 (新增)
ENABLE_SYNC_SERVICE=false
DEFAULT_SYNC_INTERVAL=300

# 通知配置
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
WECHAT_CORP_ID=your_corp_id
WECHAT_AGENT_ID=your_agent_id
WECHAT_SECRET=your_secret
```

### 访问地址

部署完成后可访问：
- **Web界面**: http://localhost
- **API文档**: http://localhost/api/v1/docs
- **数据库管理**: http://localhost:8080 (调试模式)
- **Redis管理**: http://localhost:8081 (调试模式)

## 📖 项目文档

| 文档 | 描述 |
|------|------|
| [需求文档](./REQUIREMENTS.md) | 详细的功能需求和验收标准 |
| [设计文档](./DESIGN.md) | 系统架构和技术选型说明 |
| [实现指南](./IMPLEMENTATION.md) | 代码结构和核心模块实现 |
| [价格数据库设计](./PRICE_DATABASE_DESIGN.md) | 价格数据存储和优化方案 |
| [价格订阅服务](./price-service/PRICE_SERVICE_DESIGN.md) | 实时价格采集服务设计 |
| [数据同步系统](./DATA_SYNC_DESIGN.md) | 历史数据同步功能设计 |
| [Redis分析](./REDIS_ANALYSIS.md) | Redis使用场景分析和简化建议 |

## 🛠️ 管理操作

### 服务管理

```bash
# 标准启动
./scripts/start.sh

# 完整功能启动（包含价格采集）
./scripts/start.sh --full

# 停止服务
./scripts/stop.sh

# 查看服务状态
docker-compose ps

# 查看日志
./scripts/logs.sh [服务名] [选项]

# 实时查看 API 服务日志
./scripts/logs.sh api -f

# 查看价格服务日志
./scripts/logs.sh price-service -f
```

### 数据管理

```bash
# 备份数据（包含价格数据）
./scripts/backup.sh

# 恢复数据
./scripts/restore.sh [备份名称]

# 列出可用备份
./scripts/restore.sh

# 数据库维护（清理旧数据、优化索引）
./scripts/db-maintenance.sh
```

### 同步管理

```bash
# 启动数据同步服务
docker-compose --profile sync up -d sync-service

# 查看同步状态
./scripts/logs.sh sync-service

# Web界面管理同步节点
# 访问 http://localhost/sync-management
```

### 调试模式

启动调试模式可以使用管理界面：

```bash
# 启动包含管理工具的完整服务
docker-compose --profile debug up -d

# 访问数据库管理界面
# http://localhost:8080

# 访问 Redis 管理界面
# http://localhost:8081
```

## 🏗️ 系统架构

```
远程价格服务器                     本地BTC Watcher系统
┌─────────────────┐             ┌─────────────────────────────────────────┐
│  Price Service  │────────────▶│              Web UI                     │
│  (数据采集)      │   HTTP API  │           (Vue.js + TS)                 │
│                 │   同步数据   │                                         │
│  • WebSocket    │             │  • 策略管理    • 图表展示                │
│  • 多交易所      │             │  • 信号查看    • 同步配置                │
│  • 实时存储      │             │  • 通知设置    • 系统监控                │
└─────────────────┘             └─────────────────────────────────────────┘
│                                        │                   │
├─ PostgreSQL                            │ HTTP/WebSocket    │
├─ Redis Cache                           │                   │
└─ Export API                            ▼                   ▼
                              ┌─────────────────┐  ┌─────────────────┐
                              │  Backend API    │  │  Notification   │
                              │   (FastAPI)     │  │    Service      │
                              │                 │  │                 │
                              │  • 策略管理      │  │  • 多渠道通知    │
                              │  • 信号处理      │  │  • 消息模板      │
                              │  • 数据查询      │  │  • 发送状态      │
                              └─────────────────┘  └─────────────────┘
                                        │                   │
                              ┌─────────┼─────────┐         │
                              │         │         │         │
                              ▼         ▼         ▼         ▼
                    ┌─────────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
                    │ Price Data  │ │FreqTrade│ │  Sync   │ │ Redis   │
                    │ PostgreSQL  │ │Strategies│ │Service │ │ Cache   │
                    │             │ │         │ │         │ │         │
                    │ • 分区表     │ │ • 信号   │ │ • 增量   │ │ • 价格   │
                    │ • 时序数据   │ │ • 策略   │ │ • 多源   │ │ • 会话   │
                    │ • 自动清理   │ │ • 监控   │ │ • 状态   │ │ • 队列   │
                    └─────────────┘ └─────────┘ └─────────┘ └─────────┘
```

### 技术栈

**前端**
- Vue.js 3 + TypeScript
- Element Plus UI 组件
- TradingView Lightweight Charts
- Pinia 状态管理

**后端**
- FastAPI + Python 3.11
- PostgreSQL 15 数据库（分区表优化）
- Redis 缓存和消息队列
- SQLAlchemy ORM

**价格数据服务 (新增)**
- WebSocket 多交易所数据采集
- 异步批量处理和存储
- 时间序列数据优化
- RESTful API 数据导出

**数据同步 (新增)**
- aiohttp 异步HTTP客户端
- 增量同步算法
- 多数据源支持
- 状态监控和管理

**策略引擎**
- FreqTrade 量化框架
- 自定义策略基类
- 信号输出机制

**部署**
- Docker + Docker Compose
- Nginx 反向代理
- 自动化部署脚本

## 📱 特色功能

### 价格数据管理
- **多交易所支持**: Binance、OKX、Bybit等主流交易所
- **实时数据采集**: WebSocket连接，毫秒级数据更新
- **历史数据准确**: 自建数据库，解决API历史数据不准问题
- **分区表优化**: 按时间分区，高效存储和查询
- **自动数据清理**: 智能清理策略，控制存储空间

### 分布式部署
- **独立价格服务**: 可单独部署在服务器上24小时采集数据
- **本地策略分析**: 本地运行策略，从远程同步历史数据
- **增量同步**: 智能增量同步，减少网络传输
- **多源备份**: 支持多个数据源，提高可靠性

### 高级图表功能
- **真实历史数据**: 基于自采集数据的准确K线图
- **策略信号叠加**: 实时显示策略产生的交易信号
- **多时间周期**: 1分钟到日线的完整时间周期支持
- **技术指标**: 丰富的技术分析指标库

## 📱 通知渠道配置

### Telegram Bot
1. 创建Bot: 向 @BotFather 发送 `/newbot`
2. 获取Token和Chat ID
3. 在 `.env` 中配置相关参数

### 企业微信
1. 创建企业微信应用
2. 获取Corp ID、Agent ID、Secret
3. 配置企业微信相关环境变量

### 邮件通知
支持SMTP邮件发送，配置SMTP服务器参数即可。

### 飞书通知
配置飞书Webhook URL实现群组通知。

## 🔧 开发指南

### 本地开发环境

1. **前端开发**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. **后端开发**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. **策略开发**
   ```bash
   cd freqtrade
   # 继承 BaseMonitorStrategy 类开发自定义策略
   ```

### 添加新策略

1. 在 `freqtrade/user_data/strategies/` 目录创建策略文件
2. 继承 `BaseMonitorStrategy` 基类
3. 实现 `get_buy_conditions()` 和 `get_sell_conditions()` 方法
4. 通过Web界面配置和启动策略

### 数据库管理

使用 Alembic 进行数据库迁移：

```bash
cd backend
alembic revision --autogenerate -m "描述信息"
alembic upgrade head
```

## 🔍 故障排查

### 常见问题

1. **服务启动失败**
   - 检查端口占用：`netstat -tuln | grep :80`
   - 查看服务日志：`./scripts/logs.sh`
   - 验证环境配置：确认 `.env` 文件配置正确

2. **策略不执行**
   - 检查FreqTrade日志：`./scripts/logs.sh freqtrade -f`
   - 验证交易对配置：确认交易所API连接正常
   - 检查策略文件语法

3. **通知发送失败**
   - 查看通知服务日志：`./scripts/logs.sh notification`
   - 测试通知渠道配置：通过Web界面发送测试通知
   - 检查网络连接和API凭证

### 日志查看

```bash
# 查看所有服务日志
./scripts/logs.sh all

# 实时跟踪特定服务
./scripts/logs.sh api -f

# 查看最近1小时日志
./scripts/logs.sh --since 1h
```

## 🔒 安全建议

1. **修改默认密码**: 在生产环境中务必修改所有默认密码
2. **网络安全**: 考虑使用防火墙限制端口访问
3. **HTTPS配置**: 在生产环境中启用HTTPS加密
4. **备份策略**: 定期备份重要数据和配置
5. **密钥管理**: 安全存储API密钥和访问令牌

## 🤝 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目！

1. Fork 项目仓库
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/new-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## ⚠️ 免责声明

本项目仅供学习和研究使用。加密货币交易存在高风险，请根据自己的风险承受能力谨慎投资。项目开发者不对使用本系统产生的任何投资损失承担责任。

---

**如果本项目对您有帮助，请考虑给个 ⭐ Star 支持一下！**