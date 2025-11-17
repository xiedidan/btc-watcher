# WebSocket 连接修复文档

## 问题概述

WebSocket连接失败，表现为：
- 前端无法建立ws://连接
- 通过frp代理的60001端口无法连接WebSocket
- 浏览器控制台显示连接失败或403错误

## 根本原因

1. **Nginx配置错误** - 将所有请求的Connection都设为"upgrade"，导致非WebSocket请求异常
2. **Docker网络配置** - Linux环境下`host.docker.internal`不可用
3. **FRP配置不完整** - 缺少明确的localIP配置
4. **前端WebSocket被禁用** - 代码中WebSocket连接被注释
5. **JWT Token过期** - 超过24小时有效期

## 修复方案

### 1. Nginx配置修复

**文件**: `/home/xd/project/btc-watcher/nginx/nginx.conf`

#### 添加WebSocket升级映射
```nginx
http {
    # WebSocket支持 - 动态设置Connection header
    map $http_upgrade $connection_upgrade {
        default upgrade;
        ''      close;
    }

    # ...其他配置
}
```

#### 修复Docker网络地址
```nginx
upstream frontend {
    server 172.17.0.1:3000;  # 原: host.docker.internal:3000
}

upstream backend {
    server 172.17.0.1:8000;  # 原: host.docker.internal:8000
}
```

#### 更新location块
```nginx
location /api {
    proxy_pass http://backend;
    proxy_http_version 1.1;

    # WebSocket支持 - 动态升级
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;  # 原: "upgrade"

    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 3600s;      # 1小时
    proxy_read_timeout 3600s;      # 1小时

    # 禁用缓冲以支持实时通信
    proxy_buffering off;  # 新增
}

location / {
    proxy_pass http://frontend;
    proxy_http_version 1.1;

    # WebSocket支持（Vite HMR）- 动态升级
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;  # 原: "upgrade"

    # 禁用缓冲
    proxy_buffering off;  # 新增
}
```

#### 重新加载Nginx
```bash
docker exec btc-watcher-nginx nginx -t
docker exec btc-watcher-nginx nginx -s reload
```

### 2. FRP配置优化

**文件**: `/home/xd/software/frp_0.64.0_linux_amd64/frpc.toml`

```toml
# ----------------- Web服务配置 -----------------
# TCP代理支持WebSocket（FRP的TCP模式天然支持WebSocket）
[[proxies]]
name = "freq-service"
type = "tcp"
localIP = "127.0.0.1"  # 新增：明确指定本地IP
localPort = 8501
remotePort = 60001
```

#### 重启FRP客户端
```bash
pkill -f "frpc -c"
nohup /home/xd/software/frp_0.64.0_linux_amd64/frpc \
  -c /home/xd/software/frp_0.64.0_linux_amd64/frpc.toml \
  > /tmp/frpc.log 2>&1 &
```

### 3. 前端WebSocket启用

**文件**: `/home/xd/project/btc-watcher/frontend/src/stores/user.js`

#### 启用登录时的WebSocket连接
```javascript
async function login(username, password) {
  // ...登录逻辑

  // 登录成功后连接WebSocket
  const wsStore = useWebSocketStore()
  wsStore.connect(res.access_token)

  // 订阅所有主题
  setTimeout(() => {
    wsStore.subscribe('monitoring')
    wsStore.subscribe('strategies')
    wsStore.subscribe('signals')
    wsStore.subscribe('capacity')
  }, 1000)

  return true
}
```

#### 启用登出时的WebSocket断开
```javascript
async function logout() {
  // 登出前断开WebSocket
  const wsStore = useWebSocketStore()
  wsStore.disconnect()

  token.value = ''
  user.value = null
  localStorage.removeItem('token')
}
```

## 验证方法

### 1. 本地测试（127.0.0.1:8501）
```bash
# 测试WebSocket升级
curl -v --no-buffer \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  "http://localhost:8501/api/v1/ws?token=YOUR_TOKEN"
```

期望结果：`HTTP/1.1 101 Switching Protocols` 或 `HTTP/1.1 403 Forbidden`（token失效）

### 2. 远程测试（通过FRP）

#### 获取新Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

#### 浏览器测试
1. 访问: `http://47.108.221.231:60001`
2. 登录凭据：
   - 用户名: `admin`
   - 密码: `admin123`
3. 打开开发者工具 -> Network -> WS
4. 应该看到WebSocket连接建立

#### 使用测试页面
打开浏览器访问: `file:///tmp/ws_test.html`
- 输入WebSocket URL: `ws://47.108.221.231:60001/api/v1/ws`
- 输入有效Token
- 点击"连接"按钮

### 3. 检查日志

#### Nginx日志
```bash
docker logs btc-watcher-nginx --tail 20
```

成功的WebSocket连接日志：
```
GET /api/v1/ws?token=xxx HTTP/1.1" 101
```

#### 后端日志
```bash
tail -f /tmp/backend_new.log | grep -i websocket
```

成功连接日志：
```
WebSocket client xxx_xxxxxxxx connected (user: admin)
```

#### FRP日志
```bash
cat /tmp/frpc.log
```

期望看到：
```
[freq-service] start proxy success
```

## 技术要点

### 为什么需要map指令？

Nginx的`map`指令根据请求头动态设置变量：
- 当客户端发送`Upgrade: websocket`时，`$http_upgrade`为"websocket"
- `map`将其映射到`$connection_upgrade = upgrade`
- 普通HTTP请求时，`$http_upgrade`为空，映射到`$connection_upgrade = close`

这样可以确保：
- WebSocket请求正确升级
- 普通HTTP请求保持正常连接管理

### 为什么FRP使用TCP模式？

FRP的代理类型：
- **TCP模式**: 纯TCP转发，不解析应用层协议，天然支持WebSocket
- **HTTP模式**: 解析HTTP协议，可能干扰WebSocket升级

### 为什么禁用proxy_buffering？

WebSocket需要实时双向通信：
- `proxy_buffering off` 禁用响应缓冲
- 确保消息立即转发，不会等待缓冲区满
- 降低延迟，提高实时性

## 常见问题

### Q: 为什么WebSocket连接返回403？
**A**: JWT Token过期。Token有效期24小时，需要重新登录获取新token。

### Q: 本地测试成功，但远程连接失败？
**A**: 检查：
1. FRP是否正常运行：`ps aux | grep frpc`
2. FRP日志：`cat /tmp/frpc.log`
3. 防火墙是否开放60001端口

### Q: Nginx返回502 Bad Gateway？
**A**: 后端服务未启动或无法连接。检查：
1. 后端是否运行：`curl http://localhost:8000/health`
2. Docker网络是否正常：`docker network inspect bridge`

### Q: 连接建立但收不到消息？
**A**: 检查：
1. 是否订阅了主题：发送 `{"type":"subscribe","topic":"monitoring"}`
2. 后端监控服务是否正常推送数据
3. WebSocket心跳是否正常：查看pong消息

## 监控和维护

### 定期检查
```bash
# 检查所有关键服务
ps aux | grep -E "frpc|nginx|vite|uvicorn"

# 检查WebSocket连接数
docker exec btc-watcher-nginx sh -c \
  "netstat -an | grep ESTABLISHED | grep 8501"

# 检查后端WebSocket统计
curl http://localhost:8000/api/v1/ws/stats
```

### 日志轮转
建议配置logrotate防止日志文件过大：
```bash
# /etc/logrotate.d/frpc
/tmp/frpc.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## 修复时间线

1. **2025-10-29 03:08** - 修复Nginx配置（添加map指令）
2. **2025-10-29 03:09** - 优化FRP配置（添加localIP）
3. **2025-10-29 03:09** - 启用前端WebSocket连接
4. **2025-10-29 13:09** - 重启FRP服务
5. **2025-10-29 13:09** - 验证WebSocket连接成功

## 相关文件清单

- `/home/xd/project/btc-watcher/nginx/nginx.conf` - Nginx配置
- `/home/xd/software/frp_0.64.0_linux_amd64/frpc.toml` - FRP客户端配置
- `/home/xd/project/btc-watcher/frontend/src/stores/user.js` - 前端用户状态管理
- `/home/xd/project/btc-watcher/frontend/src/stores/websocket.js` - 前端WebSocket状态管理
- `/home/xd/project/btc-watcher/frontend/src/utils/websocket.js` - WebSocket客户端
- `/home/xd/project/btc-watcher/backend/api/v1/websocket.py` - 后端WebSocket端点
- `/tmp/ws_test.html` - WebSocket测试页面

## 参考资料

- [Nginx WebSocket代理](https://nginx.org/en/docs/http/websocket.html)
- [FRP文档](https://gofrp.org/docs/)
- [WebSocket协议 RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)
- [FastAPI WebSocket文档](https://fastapi.tiangolo.com/advanced/websockets/)

---

**修复完成时间**: 2025-10-29 13:20:00
**文档版本**: 1.0
**维护者**: Claude Code Assistant
