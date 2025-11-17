# FRP + WebSocket 配置指南

## 当前架构

```
浏览器 (公网)
    ↓
47.108.221.231:60001 (FRP服务器)
    ↓ (FRP隧道)
本地 127.0.0.1:8501 (Nginx容器)
    ↓
本地 host.docker.internal:3000 (前端) + 本地 host.docker.internal:8000 (后端)
```

## FRP WebSocket支持配置

### frpc.ini (客户端配置)

确保你的FRP客户端配置包含以下内容：

```ini
[common]
server_addr = 47.108.221.231
server_port = 7000  # FRP服务器端口
token = your_token_here  # 认证token

[btc-watcher-web]
type = tcp
local_ip = 127.0.0.1
local_port = 8501
remote_port = 60001
# WebSocket支持（FRP默认支持，但确保没有禁用）
# use_encryption = false  # 如果有加密，确保不会影响WebSocket
# use_compression = false  # 如果有压缩，可能需要禁用以支持WebSocket
```

### frps.ini (服务器端配置 - 如果你管理服务器)

```ini
[common]
bind_port = 7000
token = your_token_here
# 确保没有禁用WebSocket相关功能
max_pool_count = 5
tcp_mux = true  # 多路复用（支持WebSocket）
```

## 已完成的修复

### 1. ✅ Nginx WebSocket配置已更新

```nginx
location /api {
    proxy_pass http://backend;
    proxy_http_version 1.1;

    # WebSocket支持
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # 长连接超时（1小时）
    proxy_send_timeout 3600s;
    proxy_read_timeout 3600s;
}
```

### 2. ✅ Nginx容器已重启并应用新配置

```bash
docker restart btc-watcher-nginx
```

### 3. ✅ 前端WebSocket自动适配

前端会自动使用当前页面的host来连接WebSocket：
- 本地访问 `http://localhost:3000` → `ws://localhost:3000/api/v1/ws`
- 公网访问 `http://47.108.221.231:60001` → `ws://47.108.221.231:60001/api/v1/ws`

## 测试WebSocket连接

### 方法1：浏览器测试

1. 访问 `http://47.108.221.231:60001`
2. 打开浏览器开发者工具 (F12)
3. 进入 Network 标签 → 筛选 WS
4. 登录系统
5. 查看WebSocket连接状态

**期望结果**：
```
ws://47.108.221.231:60001/api/v1/ws?token=...
Status: 101 Switching Protocols
```

### 方法2：使用wscat命令行测试

```bash
# 安装wscat
npm install -g wscat

# 测试WebSocket连接（替换YOUR_TOKEN为实际token）
wscat -c "ws://47.108.221.231:60001/api/v1/ws?token=YOUR_TOKEN"

# 如果连接成功，应该收到服务器的欢迎消息
```

### 方法3：使用curl测试WebSocket升级

```bash
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  "http://47.108.221.231:60001/api/v1/ws?token=YOUR_TOKEN"

# 期望返回 101 Switching Protocols
```

## 常见问题排查

### 问题1: WebSocket连接失败

**症状**：
```
WebSocket connection to 'ws://47.108.221.231:60001/api/v1/ws' failed
```

**排查步骤**：

1. 检查Nginx是否运行：
   ```bash
   docker ps | grep nginx
   ```

2. 检查Nginx日志：
   ```bash
   docker logs btc-watcher-nginx --tail 50
   ```

3. 检查FRP客户端日志：
   ```bash
   # 查看frpc日志，确认连接状态
   tail -f /var/log/frpc.log
   # 或者如果frpc在前台运行，查看控制台输出
   ```

4. 测试Nginx直接访问（本地）：
   ```bash
   curl -i "http://localhost:8501/api/v1/health"
   ```

### 问题2: WebSocket频繁断开

**可能原因**：
- 超时设置太短 → 已修复（现在是3600秒）
- FRP keepalive设置不当

**FRP客户端优化配置**：
```ini
[btc-watcher-web]
type = tcp
local_ip = 127.0.0.1
local_port = 8501
remote_port = 60001
# 启用心跳保持连接
heartbeat_interval = 30  # 每30秒发送心跳
heartbeat_timeout = 90   # 90秒超时
```

### 问题3: FRP不支持WebSocket

**检查方法**：
```bash
# 在FRP客户端机器上测试本地连接
wscat -c "ws://localhost:8501/api/v1/ws?token=YOUR_TOKEN"

# 如果本地能连上，但公网连不上，说明FRP配置有问题
```

**解决方案**：
- 确保FRP版本 >= 0.37.0（较新版本对WebSocket支持更好）
- 使用TCP模式而非HTTP模式（TCP模式对WebSocket支持更好）
- 检查FRP服务器端是否有防火墙限制

## 验证清单

- [ ] Nginx容器正在运行 (`docker ps | grep nginx`)
- [ ] Nginx监听8501端口 (`docker port btc-watcher-nginx`)
- [ ] Nginx配置包含WebSocket支持 (检查nginx.conf)
- [ ] Nginx超时设置为3600秒 (已验证 ✅)
- [ ] FRP客户端正在运行并连接成功
- [ ] FRP配置使用TCP模式
- [ ] 防火墙允许60001端口访问
- [ ] 前端能正常访问 `http://47.108.221.231:60001`
- [ ] WebSocket尝试连接到 `ws://47.108.221.231:60001/api/v1/ws`

## 下一步

1. **重启前端（可选）**：如果之前有修改，重新构建：
   ```bash
   cd /home/xd/project/btc-watcher/frontend
   npm run build
   ```

2. **访问测试**：
   - 浏览器访问：`http://47.108.221.231:60001`
   - 登录系统
   - 检查开发者工具中的WebSocket连接

3. **监控日志**：
   ```bash
   # Nginx日志
   docker logs -f btc-watcher-nginx

   # 后端日志（如果有WebSocket连接会显示）
   tail -f /path/to/backend/logs
   ```

## 联系支持

如果问题仍然存在，请提供：
1. FRP客户端版本和配置
2. 浏览器开发者工具中WebSocket请求的详细信息
3. Nginx日志和FRP日志
