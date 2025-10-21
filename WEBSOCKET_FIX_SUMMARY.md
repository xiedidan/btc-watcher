# WebSocket配置修复总结

## ✅ 已完成的修复

### 1. Nginx配置更新

**修复内容**：
- ✅ WebSocket超时从60秒提升到3600秒（1小时）
- ✅ WebSocket Upgrade头配置正确
- ✅ Nginx容器已重启并应用新配置

**验证**：
```bash
docker exec btc-watcher-nginx cat /etc/nginx/nginx.conf | grep proxy_read_timeout
# 输出: proxy_read_timeout 3600s; ✅
```

### 2. 前端WebSocket自动适配

**配置方式**：
- 前端会自动使用 `window.location.host` 作为WebSocket地址
- 通过 `http://47.108.221.231:60001` 访问时，WebSocket自动连接到 `ws://47.108.221.231:60001/api/v1/ws`

**相关文件**：
- `frontend/src/stores/websocket.js` - WebSocket store（已配置自动检测）
- `frontend/.env.development` - 开发环境配置
- `frontend/.env.production` - 生产环境配置

### 3. 服务状态确认

✅ 所有服务正常运行：
- Nginx容器: `btc-watcher-nginx` 监听 8501端口
- 后端API: 8000端口
- 前端Dev Server: 3000端口
- FRP客户端: 进程ID 2380

### 4. FRP映射配置

```
本地服务端口: 8501 (Nginx)
         ↓
    FRP隧道映射
         ↓
公网访问地址: 47.108.221.231:60001
```

## 🧪 测试WebSocket连接

### 步骤1: 浏览器访问

1. 打开浏览器访问：`http://47.108.221.231:60001`
2. 打开开发者工具 (F12)
3. 切换到 **Network** 标签
4. 点击 **WS** 筛选器（只显示WebSocket）
5. 登录系统（使用你的账号密码）

### 步骤2: 观察WebSocket连接

**期望看到**：
```
Name: ws
URL: ws://47.108.221.231:60001/api/v1/ws?token=eyJhbGc...
Status: 101 Switching Protocols
Type: websocket
```

**连接详情**：
- Request Headers应包含：
  - `Upgrade: websocket`
  - `Connection: Upgrade`
  - `Sec-WebSocket-Version: 13`

- Response Headers应包含：
  - `HTTP/1.1 101 Switching Protocols`
  - `Upgrade: websocket`
  - `Connection: Upgrade`

### 步骤3: 查看消息

在WS标签的**Messages**子标签中，应该看到：

**接收到的消息** (来自服务器):
```json
{
  "type": "connected",
  "available_topics": ["monitoring", "strategies", "signals", ...],
  "user": "xd1",
  "timestamp": "2025-10-21T03:30:00.000Z"
}
```

## 🔍 故障排查

### 如果WebSocket连接失败

#### 情况1: 连接被拒绝 (Connection refused)

**可能原因**：
- FRP客户端未运行
- FRP映射配置不正确

**检查命令**：
```bash
# 检查FRP进程
ps aux | grep frpc

# 检查FRP日志
tail -f /path/to/frpc.log

# 本地测试Nginx
curl -I http://localhost:8501/api/v1/health
```

#### 情况2: 返回404 Not Found

**可能原因**：
- 后端WebSocket端点未正确注册
- Nginx代理配置路径不匹配

**检查后端**：
```bash
# 检查后端日志
cd /home/xd/project/btc-watcher/backend
# 查看main.py是否包含WebSocket路由

# 测试后端直接访问
curl -I http://localhost:8000/api/v1/ws
```

#### 情况3: 连接后立即断开

**可能原因**：
- Token无效或过期
- 后端WebSocket逻辑有问题

**解决方案**：
1. 重新登录获取新token
2. 检查后端日志

### 前端控制台错误

如果看到：
```
WebSocket connection to 'ws://47.108.221.231:60001/api/v1/ws?token=...' failed
```

**检查清单**：
- [ ] Nginx容器运行中：`docker ps | grep nginx`
- [ ] FRP客户端运行中：`ps aux | grep frpc`
- [ ] 后端API运行中：`curl http://localhost:8000/api/v1/health`
- [ ] 浏览器Network标签中WebSocket请求的Status Code
- [ ] Nginx日志：`docker logs btc-watcher-nginx --tail 50`

## 📊 监控WebSocket

### 实时监控Nginx日志

```bash
docker logs -f btc-watcher-nginx
```

成功的WebSocket连接应该显示类似：
```
172.17.0.1 - - [21/Oct/2025:03:30:00 +0000] "GET /api/v1/ws?token=... HTTP/1.1" 101 0 ...
```

注意状态码是 **101**（Switching Protocols），而不是200或其他。

### 监控后端WebSocket

```bash
# 如果后端有日志输出
cd /home/xd/project/btc-watcher/backend
python main.py
# 查看控制台输出，应该有WebSocket连接的日志
```

## 🎯 预期行为

### 连接成功后

1. **系统监控数据推送**：
   - 每10秒接收一次系统监控数据
   - CPU、内存、磁盘使用率更新

2. **策略状态更新**：
   - 实时显示运行中的策略数量
   - 策略启动/停止事件

3. **新信号推送**：
   - 交易信号实时推送
   - 信号列表自动更新

4. **通知消息**：
   - 系统通知实时显示
   - 浏览器通知（如果已授权）

## 📁 相关文件

- `/home/xd/project/btc-watcher/nginx/nginx.conf` - Nginx配置
- `/home/xd/project/btc-watcher/frontend/src/stores/websocket.js` - WebSocket store
- `/home/xd/project/btc-watcher/frontend/src/utils/websocket.js` - WebSocket客户端
- `/home/xd/project/btc-watcher/backend/api/v1/websocket.py` - WebSocket后端

## 🚀 下一步

1. **测试WebSocket连接**：按照上述步骤测试
2. **检查FRP配置**：确保FRP支持WebSocket（见 FRP_WEBSOCKET_GUIDE.md）
3. **报告问题**：如果仍有问题，提供：
   - 浏览器开发者工具截图（Network > WS标签）
   - Nginx日志
   - FRP日志
   - 后端日志

## 🔧 快速诊断

运行诊断脚本：
```bash
./diagnose-websocket.sh
```

## 📖 参考文档

- `FRP_WEBSOCKET_GUIDE.md` - FRP WebSocket配置详细指南
- `WEBSOCKET_TROUBLESHOOTING.md` - WebSocket故障排查指南

---

**最后更新**：2025-10-21
**状态**：✅ Nginx配置已修复，等待FRP配置确认
