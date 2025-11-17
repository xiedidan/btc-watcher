# BTC Watcher 常见问题解答 (FAQ)

## 🎯 产品概述

### Q: BTC Watcher是什么？
**A:** BTC Watcher是一个专业的加密货币信号监控和分析系统，支持999个并发FreqTrade策略实例。它提供实时监控、智能通知、多维度分析和完整的Web管理界面。

### Q: BTC Watcher的主要功能有哪些？
**A:** 主要功能包括：
- 🚀 **999并发策略支持** - 智能端口池管理
- 📊 **实时信号监控** - 自动强度分级(强/中/弱/忽略)
- 📈 **多维度监控** - CPU、内存、磁盘、策略状态
- 📱 **多渠道通知** - Telegram、企业微信、飞书、邮件
- 🎨 **现代化界面** - Vue 3 + Element Plus响应式设计
- 🔐 **安全认证** - JWT令牌认证机制

### Q: BTC Watcher适合什么用户使用？
**A:** 适合以下用户：
- **个人投资者** - 管理3-5个策略
- **小型团队** - 管理10-20个策略
- **专业团队** - 管理50-100个策略
- **机构用户** - 管理100-999个策略

## 🚀 部署和安装

### Q: 部署BTC Watcher需要什么系统要求？
**A:** 系统要求：
- **最低配置**: 2核CPU + 4GB内存 + 20GB存储
- **推荐配置**: 8核CPU + 16GB内存 + 100GB SSD
- **软件依赖**: Docker 20.10+ 和 Docker Compose 2.0+
- **操作系统**: Linux (推荐Ubuntu 20.04+), macOS, Windows WSL2

### Q: 部署过程复杂吗？需要多长时间？
**A:** 部署很简单：
- **快速部署**: 5-10分钟（使用Docker Compose）
- **完整部署**: 30-60分钟（包含配置和优化）
- **一键部署**: 提供自动化脚本，简化部署流程

### Q: 是否支持云服务器部署？
**A:** 支持主流云平台：
- ✅ AWS EC2、Lightsail
- ✅ Google Cloud Platform
- ✅ Microsoft Azure
- ✅ 阿里云、腾讯云、华为云
- ✅ DigitalOcean、Linode、Vultr

### Q: 如何升级到新版本？
**A:** 升级步骤：
```bash
# 1. 备份数据
./scripts/maintenance/backup.sh

# 2. 获取新版本
git pull origin main

# 3. 更新容器
docker-compose pull
docker-compose up -d

# 4. 验证升级
curl http://localhost:8000/api/v1/system/info
```

## 🔧 配置和使用

### Q: 如何配置交易所API？
**A:** 在策略配置中设置：
```json
{
  "exchange": "binance",
  "exchange_config": {
    "api_key": "your_api_key",
    "api_secret": "your_api_secret",
    "sandbox": false
  }
}
```

### Q: 支持哪些交易所？
**A:** 支持主流交易所：
- ✅ Binance (币安)
- ✅ Coinbase Pro
- ✅ Kraken
- ✅ Huobi (火币)
- ✅ OKEx
- ✅ KuCoin
- ✅ 其他FreqTrade支持的交易所

### Q: 如何设置通知？
**A:** 在环境变量中配置：
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 邮件
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_password

# 企业微信
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
```

### Q: 可以自定义策略吗？
**A:** 支持多种方式：
- **内置策略** - 提供常用策略模板
- **自定义策略** - 支持Python编写自定义策略
- **策略上传** - 支持上传策略文件
- **参数调整** - 灵活配置策略参数

## 📊 性能和容量

### Q: 系统最大支持多少个策略？
**A:** 理论最大支持999个并发策略：
- **端口范围**: 8081-9080 (共999个端口)
- **实际建议**: 根据硬件配置调整
- **小规模**: 3-20个策略 (4核8G)
- **中等规模**: 20-100个策略 (8核16G)
- **大规模**: 100-999个策略 (32核64G+)

### Q: 系统性能如何？API响应时间？
**A:** 性能指标：
- **API响应时间**: <100ms (90%请求)
- **并发处理**: 1000+ QPS
- **数据库连接**: 20连接池
- **内存使用**: 基础服务约2GB
- **CPU使用**: 根据策略数量线性增长

### Q: 如何监控系统性能？
**A:** 提供多维度监控：
- **系统指标**: CPU、内存、磁盘、网络
- **应用指标**: API响应时间、错误率
- **业务指标**: 策略状态、信号数量、容量使用
- **实时告警**: 超过阈值自动通知

### Q: 支持负载均衡吗？
**A:** 支持多种负载均衡方案：
- **Nginx负载均衡** - 内置配置
- **HAProxy** - 高性能负载均衡
- **云负载均衡** - AWS ELB、阿里云SLB等
- **容器编排** - Kubernetes Service

## 🔐 安全和隐私

### Q: 系统安全性如何？
**A:** 多层安全防护：
- **认证授权** - JWT令牌 + 角色权限
- **数据加密** - 敏感数据加密存储
- **传输加密** - HTTPS/TLS传输
- **访问控制** - IP白名单、防暴力破解
- **安全审计** - 完整操作日志

### Q: 如何保护API密钥？
**A:** 密钥保护措施：
- **环境变量** - 不硬编码在代码中
- **加密存储** - 数据库中加密保存
- **访问控制** - 限制密钥文件权限
- **定期轮换** - 支持密钥定期更新
- **审计日志** - 记录密钥使用情况

### Q: 是否符合数据保护法规？
**A:** 符合主要数据保护要求：
- **GDPR** - 欧盟数据保护法规
- **CCPA** - 加州消费者隐私法案
- **数据本地化** - 支持数据本地存储
- **隐私设计** - 最小化数据收集
- **用户控制** - 用户数据自主控制

### Q: 如何备份和恢复数据？
**A:** 提供完整备份方案：
```bash
# 自动备份
./scripts/maintenance/backup.sh

# 手动备份
docker-compose exec db pg_dump -U btc_watcher btc_watcher > backup.sql

# 恢复数据
docker-compose exec -T db psql -U btc_watcher -d btc_watcher < backup.sql
```

## 🛠️ 技术问题

### Q: 系统基于什么技术栈？
**A:** 现代化技术栈：
- **后端**: Python 3.11 + FastAPI + SQLAlchemy 2.0
- **前端**: Vue 3 + Element Plus + ECharts
- **数据库**: PostgreSQL 15 + Redis 7.2
- **基础设施**: Docker + Nginx + Docker Compose
- **通信**: REST API + WebSocket

### Q: 支持哪些部署方式？
**A:** 多种部署选项：
- **Docker Compose** - 推荐方式，简单快速
- **Docker Swarm** - 容器编排
- **Kubernetes** - 云原生部署
- **传统部署** - 直接安装（高级用户）

### Q: 如何进行开发环境搭建？
**A:** 开发环境搭建：
```bash
# 1. 克隆代码
git clone https://github.com/yourusername/btc-watcher.git
cd btc-watcher

# 2. 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 3. 后端开发
cd backend
pip install -r requirements-dev.txt
python main.py

# 4. 前端开发
cd frontend
npm install
npm run dev
```

### Q: 是否提供API接口？
**A:** 提供完整REST API：
- **认证接口** - 用户注册、登录、Token管理
- **策略接口** - 策略CRUD、启动停止
- **信号接口** - 信号查询、统计、Webhook
- **系统接口** - 健康检查、容量查询、指标监控
- **WebSocket** - 实时数据推送

详细API文档：http://localhost:8000/docs

## 💰 成本和许可

### Q: BTC Watcher是免费的还是收费的？
**A:** 开源免费：
- **核心功能** - 完全免费，MIT许可证
- **商业使用** - 允许商业用途
- **修改分发** - 允许修改和再分发
- **技术支持** - 社区支持免费，专业支持收费

### Q: 运行成本大概是多少？
**A:** 运行成本估算：

**云服务器成本（月）**:
- **小规模** (4核8G): $20-50/月
- **中等规模** (8核16G): $50-100/月
- **大规模** (16核32G): $100-200/月

**其他成本**:
- **网络流量** - 通常包含在服务器费用中
- **存储** - $0.10-0.20/GB/月
- **备份** - $0.05-0.10/GB/月

### Q: 是否提供技术支持服务？
**A:** 多层次技术支持：
- **社区支持** - 免费，通过GitHub Issues
- **文档支持** - 免费，完整技术文档
- **邮件支持** - 免费，一般性问题
- **专业支持** - 收费，7x24小时
- **现场支持** - 收费，企业级服务

## 🔧 故障排除

### Q: 系统无法启动怎么办？
**A:** 逐步排查：
```bash
# 1. 检查Docker环境
docker --version
docker compose version

# 2. 检查端口占用
netstat -tulpn | grep -E ':80|:8000'

# 3. 查看错误日志
docker-compose logs --tail=50

# 4. 验证配置文件
./scripts/diagnostics/verify_deployment.sh

# 5. 一键诊断
./scripts/diagnostics/full_diagnosis.sh
```

### Q: 策略无法启动怎么办？
**A:** 常见原因和解决：
- **端口冲突** - 检查端口占用，重启系统
- **配置错误** - 验证策略配置文件
- **容量不足** - 检查系统容量，停止其他策略
- **权限问题** - 检查文件权限和用户权限

### Q: 信号接收失败怎么办？
**A:** 排查步骤：
1. **检查Webhook配置** - 确保URL格式正确
2. **测试网络连通性** - 容器间网络通信
3. **查看日志** - 检查信号接收日志
4. **验证API** - 手动测试信号接收API

详细故障排查：查看[故障排查指南](troubleshooting.md)

### Q: 性能缓慢如何优化？
**A:** 性能优化建议：
- **数据库优化** - 添加索引，优化查询
- **缓存配置** - 启用Redis缓存
- **资源扩容** - 增加CPU和内存
- **负载均衡** - 多实例部署

## 📈 高级功能

### Q: 支持算法交易吗？
**A:** 支持算法交易：
- **自动执行** - 基于信号自动交易
- **风险管理** - 内置风险控制机制
- **回测功能** - 历史数据回测
- **参数优化** - 自动参数调优

### Q: 可以集成其他系统吗？
**A:** 提供多种集成方式：
- **REST API** - 标准HTTP接口
- **WebSocket** - 实时数据推送
- **Webhook** - 事件回调通知
- **数据库集成** - 直接数据库访问

### Q: 支持移动端访问吗？
**A:** 支持移动设备：
- **响应式设计** - 自适应各种屏幕尺寸
- **PWA支持** - 可安装为桌面应用
- **移动端优化** - 触摸友好的界面
- **离线功能** - 缓存常用数据

### Q: 是否支持多语言？
**A:** 国际化支持：
- **中文** - 完整中文界面
- **英文** - 完整英文界面
- **扩展性** - 易于添加新语言
- **自动检测** - 根据浏览器设置

## 🔄 更新和维护

### Q: 如何更新到最新版本？
**A:** 更新步骤：
```bash
# 1. 备份数据
./scripts/maintenance/backup.sh

# 2. 获取更新
git pull origin main

# 3. 更新容器
docker-compose pull
docker-compose up -d

# 4. 验证更新
curl http://localhost:8000/api/v1/system/info
```

### Q: 如何进行数据备份？
**A:** 备份方案：
```bash
# 自动备份
./scripts/maintenance/backup.sh

# 数据库备份
docker-compose exec db pg_dump -U btc_watcher btc_watcher > backup.sql

# 文件备份
tar -czf strategies_backup.tar.gz data/strategies/
```

### Q: 系统维护需要注意什么？
**A:** 维护建议：
- **定期备份** - 设置自动备份计划
- **监控告警** - 配置系统监控
- **日志管理** - 定期清理日志文件
- **安全更新** - 及时更新安全补丁
- **性能监控** - 定期检查系统性能

## 📚 学习和资源

### Q: 如何学习使用BTC Watcher？
**A:** 学习资源：
- **快速开始** - [5分钟上手指南](getting-started.md)
- **用户手册** - [详细功能说明](user-guide.md)
- **视频教程** - [官方YouTube频道](https://youtube.com/btc-watcher)
- **社区论坛** - [用户交流社区](https://community.btc-watcher.com)

### Q: 有示例策略吗？
**A:** 提供示例策略：
- **趋势策略** - 基于MACD的趋势跟踪
- **震荡策略** - 基于RSI的区间交易
- **突破策略** - 基于布林带的突破交易
- **组合策略** - 多指标综合策略

### Q: 如何贡献代码？
**A:** 贡献指南：
1. Fork项目仓库
2. 创建功能分支
3. 提交代码变更
4. 创建Pull Request
5. 通过代码审查

详细指南：查看[贡献指南](../development/)

---

## 💡 常见问题快速查找

### 按问题类型
- **部署问题** - 查看[部署指南](deployment-guide.md)
- **配置问题** - 查看[用户手册](user-guide.md)
- **故障问题** - 查看[故障排查](troubleshooting.md)
- **开发问题** - 查看[开发指南](../development/)

### 按用户角色
- **新用户** - 从[快速开始](getting-started.md)开始
- **管理员** - 查看[部署指南](deployment-guide.md)
- **开发者** - 查看[API参考](api-reference.md)
- **运维人员** - 查看[运维指南](../operations/)

### 按严重程度
- **紧急问题** - 系统无法访问、数据丢失
- **重要问题** - 功能异常、性能下降
- **一般问题** - 配置疑问、使用帮助

---

**❓ 问题未解决？**

如果以上FAQ未能解决您的问题，请：
1. 查看详细的[故障排查指南](troubleshooting.md)
2. 在[GitHub Issues](https://github.com/yourusername/btc-watcher/issues)提交问题
3. 加入我们的[Discord社区](https://discord.gg/btc-watcher)寻求帮助
4. 发送邮件至：support@btc-watcher.com

**📞 联系方式**:
- 📧 Email: support@btc-watcher.com
- 💬 Discord: https://discord.gg/btc-watcher
- 📖 文档: https://docs.btc-watcher.com
- 🐛 Issues: https://github.com/yourusername/btc-watcher/issues

---

**版本**: v1.0.0
**更新日期**: 2025-10-15
**维护团队**: BTC Watcher Documentation Team