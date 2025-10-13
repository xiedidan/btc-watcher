# BTC Watcher

<div align="center">

![BTC Watcher Logo](https://via.placeholder.com/150)

**加密货币信号监控与分析系统**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-teal.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README_EN.md) | 简体中文

</div>

---

## 📖 项目简介

BTC Watcher 是一个专业的加密货币信号监控和分析系统，支持999个并发FreqTrade策略实例，提供实时监控、智能通知和完整的管理界面。

### ✨ 核心特性

- 🚀 **超大规模并发**: 支持999个FreqTrade策略同时运行
- 🎯 **智能信号分级**: 自动分析信号强度(强/中/弱)
- 📊 **实时监控**: CPU、内存、磁盘、策略状态全方位监控
- 📱 **多渠道通知**: 支持Telegram、企业微信、飞书、邮件
- 🔐 **安全认证**: JWT令牌认证，保护您的数据
- 🎨 **现代化界面**: Vue 3 + Element Plus 响应式设计

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     BTC Watcher System                        │
└─────────────────────────────────────────────────────────────┘

Frontend (Vue 3)  →  Nginx  →  Backend (FastAPI)
                                    ↓
                        ┌───────────┼───────────┐
                        ↓           ↓           ↓
                   PostgreSQL    Redis    FreqTrade Gateway
                                              ↓
                                  999 FreqTrade Instances
                                  (Port: 8081-9080)
```

---

## 🚀 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (仅开发环境)
- Python 3.11+ (仅开发环境)

### 一键部署

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/btc-watcher.git
cd btc-watcher

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 文件配置数据库密码和通知渠道

# 3. 启动所有服务
docker-compose up -d

# 4. 访问系统
# 前端: http://localhost
# API文档: http://localhost:8000/docs
```

### 测试部署

```bash
# 1. 验证部署环境
./verify_deployment.sh

# 2. 启动服务
make up
# 或
./scripts/start.sh

# 3. 运行验证测试
make test-verify

# 4. 运行API集成测试
make test
```

查看详细测试指南: [TESTING.md](TESTING.md)

### 开发环境

#### 后端开发

```bash
cd backend
pip install -r requirements.txt
python main.py
```

访问 API 文档: http://localhost:8000/docs

#### 前端开发

```bash
cd frontend
npm install
npm run dev
```

访问前端: http://localhost:3000

---

## 📊 功能特性

### 后端功能

- ✅ 用户认证与授权 (JWT)
- ✅ 策略CRUD管理
- ✅ 策略启动/停止控制
- ✅ 999个并发策略支持
- ✅ 智能端口池管理
- ✅ 交易信号接收与存储
- ✅ 信号强度自动分级
- ✅ 实时系统监控
- ✅ 多渠道通知推送
- ✅ 容量追踪与告警

### 前端功能

- ✅ 用户登录/注册
- ✅ 仪表盘数据可视化
- ✅ 策略管理界面
- ✅ 信号列表与详情
- ✅ 系统监控面板
- ✅ 响应式设计

---

## 📈 技术栈

### 后端

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.104 | Web框架 |
| SQLAlchemy | 2.0 | ORM (异步) |
| PostgreSQL | 15 | 数据库 |
| Redis | 7 | 缓存 |
| Docker | 20.10+ | 容器化 |

### 前端

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.4 | 前端框架 |
| Vite | 5.0 | 构建工具 |
| Element Plus | 2.5 | UI组件库 |
| Pinia | 2.1 | 状态管理 |
| ECharts | 5.4 | 图表库 |
| Axios | 1.6 | HTTP客户端 |

---

## 📂 项目结构

```
btc-watcher/
├── backend/                # 后端 (Python/FastAPI)
│   ├── api/               # API路由
│   ├── core/              # 核心模块
│   ├── services/          # 服务层
│   ├── models/            # 数据模型
│   ├── database/          # 数据库配置
│   └── main.py           # 主应用
├── frontend/              # 前端 (Vue 3)
│   ├── src/
│   │   ├── api/          # API客户端
│   │   ├── stores/       # 状态管理
│   │   ├── router/       # 路由
│   │   ├── views/        # 页面组件
│   │   └── layouts/      # 布局组件
│   └── package.json
├── sql/                   # 数据库脚本
├── docker-compose.yml     # Docker编排
└── README.md
```

---

## 🔧 配置说明

### 环境变量

编辑 `backend/.env` 文件：

```bash
# 数据库
DATABASE_URL=postgresql://btc_watcher:password@db:5432/btc_watcher
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_PASSWORD=your_redis_password

# JWT密钥
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key

# FreqTrade
MAX_CONCURRENT_STRATEGIES=999
FREQTRADE_BASE_PORT=8081
FREQTRADE_MAX_PORT=9080

# 通知配置
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@email.com
SMTP_PASSWORD=your_password
```

---

## 📝 API文档

启动后端服务后，访问自动生成的API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要API端点

#### 认证
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/token` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户

#### 策略管理
- `GET /api/v1/strategies/` - 获取策略列表
- `POST /api/v1/strategies/` - 创建策略
- `POST /api/v1/strategies/{id}/start` - 启动策略
- `POST /api/v1/strategies/{id}/stop` - 停止策略

#### 信号
- `GET /api/v1/signals/` - 获取信号列表
- `POST /api/v1/signals/webhook/{strategy_id}` - 接收FreqTrade信号

#### 系统
- `GET /api/v1/system/capacity` - 获取系统容量
- `GET /api/v1/system/health` - 健康检查

---

## 🎯 使用场景

### 个人投资者 (3-5个策略)
- 推荐配置: 4核CPU + 8GB内存
- 适用场景: 个人量化交易

### 小型团队 (10-20个策略)
- 推荐配置: 8核CPU + 16GB内存
- 适用场景: 小型量化团队

### 专业团队 (50-100个策略)
- 推荐配置: 16核CPU + 64GB内存
- 适用场景: 专业量化机构

### 机构级别 (100-999个策略)
- 推荐配置: 32核CPU + 128GB+内存
- 适用场景: 大型量化基金

---

## 🔒 安全建议

1. **修改默认密码**: 生产环境必须修改所有默认密码
2. **使用HTTPS**: 配置SSL证书保护API通信
3. **定期备份**: 定期备份数据库和配置文件
4. **访问控制**: 限制数据库和Redis的网络访问
5. **日志审计**: 定期检查系统日志

---

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| 最大并发策略 | 999个 |
| API响应时间 | < 100ms (90%) |
| 并发请求 | 1000+ QPS |
| 数据库连接池 | 5-20连接 |
| 端口范围 | 8081-9080 |

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3 UI组件库
- [FreqTrade](https://www.freqtrade.io/) - 加密货币交易机器人
- [PostgreSQL](https://www.postgresql.org/) - 强大的开源数据库
- [Redis](https://redis.io/) - 内存数据库

---

## 📮 联系方式

- **项目地址**: https://github.com/yourusername/btc-watcher
- **问题反馈**: https://github.com/yourusername/btc-watcher/issues
- **邮箱**: your.email@example.com

---

## 🗺️ 路线图

- [x] 核心功能实现
- [x] 999个并发策略支持
- [x] 多渠道通知系统
- [ ] WebSocket实时推送
- [ ] 策略性能分析
- [ ] 历史数据回测
- [ ] 移动端应用
- [ ] 高级图表分析

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by BTC Watcher Team

</div>
