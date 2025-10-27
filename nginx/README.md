# Alpha环境Nginx反向代理配置说明

## 配置概述

本配置将8501端口反向代理到前端的3000端口，实现：
- 前端开发服务器运行在 `localhost:3000`
- 后端API服务运行在 `localhost:8000`
- Nginx在8501端口提供统一的外部访问入口
- 支持WebSocket和API代理

## 架构图

```
外网访问 (8501端口)
    ↓
Nginx 反向代理
    ↓
    ├─→ Frontend (3000) - Vue.js开发服务器
    └─→ Backend API (8000) - FastAPI服务
```

## 快速开始

### 1. 自动安装（推荐）

运行以下命令自动完成所有配置：

```bash
sudo ./setup-nginx-alpha.sh
```

### 2. 手动安装

如果需要手动配置，请按以下步骤操作：

#### 步骤1: 安装Nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

#### 步骤2: 部署配置文件

```bash
# 复制配置文件到Nginx配置目录
sudo cp nginx/btc-watcher-alpha.conf /etc/nginx/sites-available/

# 创建软链接启用配置
sudo ln -s /etc/nginx/sites-available/btc-watcher-alpha.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

#### 步骤3: 确认服务运行状态

```bash
# 检查前端服务（应该在3000端口）
lsof -i :3000

# 检查后端服务（应该在8000端口）
lsof -i :8000

# 检查Nginx（应该在8501端口）
lsof -i :8501
```

## 访问方式

配置完成后，可以通过以下方式访问：

- **本地访问**: http://localhost:8501
- **局域网访问**: http://192.168.5.112:8501
- **外网访问**: 通过FRP配置后访问（见下文）

## 防火墙配置

如需外网访问，需要开放8501端口：

```bash
# Ubuntu/Debian
sudo ufw allow 8501
sudo ufw reload

# 查看防火墙状态
sudo ufw status
```

## FRP内网穿透配置

编辑FRP客户端配置文件 `frpc.ini`:

```ini
[common]
server_addr = <你的FRP服务器地址>
server_port = 7000
token = <你的认证令牌>

[btc-watcher-alpha]
type = tcp
local_ip = 127.0.0.1
local_port = 8501           # Nginx监听端口
remote_port = 60001         # 外网访问端口
```

启动FRP客户端：

```bash
./frpc -c frpc.ini
```

访问地址：`http://<FRP服务器IP>:60001`

## 日志查看

```bash
# Nginx访问日志
tail -f /var/log/nginx/btc-watcher-access.log

# Nginx错误日志
tail -f /var/log/nginx/btc-watcher-error.log

# 实时查看所有Nginx日志
sudo tail -f /var/log/nginx/*.log
```

## 故障排查

### 问题1: 8501端口无法访问

```bash
# 检查Nginx是否运行
sudo systemctl status nginx

# 检查端口是否监听
sudo netstat -tulnp | grep 8501

# 重启Nginx
sudo systemctl restart nginx
```

### 问题2: 502 Bad Gateway

说明Nginx无法连接到后端服务，检查：

```bash
# 确认前端在3000端口运行
lsof -i :3000

# 确认后端在8000端口运行
lsof -i :8000

# 如果服务未运行，启动它们
cd frontend && npm run dev &
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

### 问题3: WebSocket连接失败

检查Nginx配置中的WebSocket相关设置，确保包含：

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## 配置文件说明

### nginx/btc-watcher-alpha.conf

主要配置项：

- `listen 8501`: Nginx监听端口
- `location /`: 前端代理到3000端口
- `location /api/`: API代理到8000端口
- `location /ws/`: WebSocket代理到8000端口

## 维护命令

```bash
# 重启Nginx
sudo systemctl restart nginx

# 重新加载配置（不中断服务）
sudo systemctl reload nginx

# 查看Nginx状态
sudo systemctl status nginx

# 测试配置文件语法
sudo nginx -t

# 停止Nginx
sudo systemctl stop nginx

# 启动Nginx
sudo systemctl start nginx
```

## 性能优化（可选）

如需优化性能，可以编辑 `/etc/nginx/nginx.conf` 添加：

```nginx
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
```

## 安全建议

1. **启用HTTPS** (生产环境强烈推荐):
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

2. **限制访问IP** (可选):
   在Nginx配置中添加：
   ```nginx
   allow 192.168.0.0/16;
   allow 10.0.0.0/8;
   deny all;
   ```

3. **添加认证** (可选):
   ```bash
   sudo apt-get install apache2-utils
   sudo htpasswd -c /etc/nginx/.htpasswd username
   ```

   在Nginx配置中添加：
   ```nginx
   auth_basic "Restricted Access";
   auth_basic_user_file /etc/nginx/.htpasswd;
   ```

## 相关文档

- [设计文档](../DESIGN.md) - 第4.3节 Alpha部署环境
- [Nginx官方文档](https://nginx.org/en/docs/)
- [FRP官方文档](https://github.com/fatedier/frp)
