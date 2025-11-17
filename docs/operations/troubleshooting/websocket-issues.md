# WebSocket连接问题解决方案

## 问题诊断

错误信息：
```
WebSocket connection to 'ws://47.108.221.231:60001/api/v1/ws?token=...' failed
```

**原因**：前端尝试连接到60001端口，但该端口没有运行任何服务。

## 当前服务状态

- ✅ 后端API: `http://localhost:8000`
- ✅ 前端Dev Server: `http://localhost:3000`
- ❌ Nginx: 未运行（应该在8501或80端口）
- ❌ 端口60001: 无服务

## 解决方案

### 方案1：本地开发（推荐）

如果你在本地开发，请通过以下地址访问：

```bash
# 访问前端（Vite Dev Server会自动代理WebSocket）
http://localhost:3000

# WebSocket会自动连接到:
ws://localhost:3000/api/v1/ws
# 然后Vite代理到 ws://localhost:8000/api/v1/ws
```

**步骤**：
1. 确保后端在运行：
   ```bash
   cd /home/xd/project/btc-watcher/backend
   python main.py
   ```

2. 确保前端在运行：
   ```bash
   cd /home/xd/project/btc-watcher/frontend
   npm run dev
   ```

3. 浏览器访问：`http://localhost:3000`

### 方案2：通过Nginx代理（生产环境）

如果需要通过外部IP访问，需要启动Nginx：

```bash
# 检查nginx配置
cat nginx/nginx.conf

# 启动nginx（如果使用Docker）
docker-compose up -d nginx

# 或者本地nginx
sudo nginx -c /home/xd/project/btc-watcher/nginx/nginx.conf
```

Nginx配置监听8501端口，访问：
```
http://47.108.221.231:8501
```

### 方案3：Docker Compose部署

使用Docker Compose一键启动所有服务：

```bash
cd /home/xd/project/btc-watcher
docker-compose up -d
```

服务会在以下端口：
- Nginx: `http://localhost:80` 或 `http://localhost:443` (HTTPS)
- API: `http://localhost:8000` (内部)
- DB: `localhost:5432`
- Redis: `localhost:6379`

### 方案4：配置Vite Dev Server允许外部访问

如果你想通过外部IP访问Vite dev server：

1. Vite已配置监听 `0.0.0.0:3000`
2. 访问：`http://47.108.221.231:3000`
3. WebSocket会自动使用相同的host和port

**注意**：需要确保防火墙允许3000端口访问。

## 已应用的修复

我已经做了以下修改：

### 1. 创建了 `.env.development`

```env
VITE_WS_URL=ws://localhost:8000
```

这会让WebSocket直接连接到后端，绕过Vite代理。

### 2. 更新了 `vite.config.js`

启用了WebSocket代理：
```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    ws: true  // ✅ 启用WebSocket代理
  }
}
```

### 3. 更新了 `websocket.js` store

添加了更详细的日志，方便调试。

## 推荐做法

**开发环境**：
- 删除或注释掉 `.env.development` 中的 `VITE_WS_URL`
- 直接访问 `http://localhost:3000`
- WebSocket会通过Vite代理自动连接到后端

**生产环境**：
- 使用Docker Compose部署
- Nginx处理反向代理和WebSocket升级
- 通过80/443端口访问

## 验证步骤

1. 重启前端dev server：
   ```bash
   cd /home/xd/project/btc-watcher/frontend
   # 按Ctrl+C停止当前dev server
   npm run dev
   ```

2. 打开浏览器访问 `http://localhost:3000`

3. 打开浏览器开发者工具 (F12) -> Network -> WS 标签

4. 登录系统，查看WebSocket连接状态

5. 应该看到：
   ```
   ws://localhost:3000/api/v1/ws?token=...
   Status: 101 Switching Protocols
   ```

## 如果还有问题

请提供以下信息：
1. 你是如何访问前端的？（localhost还是外部IP？）
2. 浏览器控制台的完整错误信息
3. 网络标签中WebSocket请求的详细信息
