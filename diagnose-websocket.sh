#!/bin/bash

echo "🔍 BTC Watcher WebSocket 诊断工具"
echo "================================"
echo ""

# 检查Docker
echo "📦 检查Docker服务..."
if docker ps > /dev/null 2>&1; then
    echo "✅ Docker正在运行"
else
    echo "❌ Docker未运行或无权限"
    exit 1
fi
echo ""

# 检查Nginx容器
echo "🌐 检查Nginx容器..."
if docker ps | grep -q "btc-watcher-nginx"; then
    echo "✅ Nginx容器正在运行"
    NGINX_PORT=$(docker port btc-watcher-nginx 2>/dev/null | grep 8501 | cut -d: -f2)
    if [ -n "$NGINX_PORT" ]; then
        echo "   端口映射: 0.0.0.0:$NGINX_PORT -> 8501"
    fi
else
    echo "❌ Nginx容器未运行"
    echo "   启动命令: docker start btc-watcher-nginx"
fi
echo ""

# 检查Backend
echo "🔧 检查后端服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端API (8000) 正在运行"
else
    echo "❌ 后端API (8000) 未响应"
fi
echo ""

# 检查Frontend
echo "🎨 检查前端服务..."
if lsof -i :3000 > /dev/null 2>&1; then
    echo "✅ 前端Dev Server (3000) 正在运行"
else
    echo "❌ 前端Dev Server (3000) 未运行"
    echo "   启动命令: cd frontend && npm run dev"
fi
echo ""

# 检查Nginx配置
echo "⚙️  检查Nginx WebSocket配置..."
WS_TIMEOUT=$(docker exec btc-watcher-nginx cat /etc/nginx/nginx.conf 2>/dev/null | grep "proxy_read_timeout" | head -1 | awk '{print $2}')
if [ -n "$WS_TIMEOUT" ]; then
    echo "   WebSocket超时设置: $WS_TIMEOUT"
    if [[ "$WS_TIMEOUT" == "3600s;" ]]; then
        echo "✅ 超时设置正确（1小时）"
    else
        echo "⚠️  超时设置较短，建议设为3600s"
    fi
else
    echo "⚠️  无法读取Nginx配置"
fi
echo ""

# 检查WebSocket端点
echo "🔌 检查WebSocket端点..."
if curl -i -s --max-time 2 "http://localhost:8501/api/v1/health" | grep -q "200 OK"; then
    echo "✅ Nginx代理到后端正常"
else
    echo "❌ Nginx代理到后端失败"
fi
echo ""

# 网络测试
echo "🌍 网络连通性测试..."
echo "   本地Nginx: http://localhost:8501"
echo "   公网地址: http://47.108.221.231:60001"
echo ""
echo "   测试命令:"
echo "   curl -I http://localhost:8501/api/v1/health"
echo "   curl -I http://47.108.221.231:60001/api/v1/health"
echo ""

# FRP状态
echo "🚇 FRP状态检查..."
if ps aux | grep -q "[f]rpc"; then
    echo "✅ FRP客户端正在运行"
    echo "   进程: $(ps aux | grep "[f]rpc" | awk '{print $2}')"
else
    echo "⚠️  未检测到FRP客户端进程"
    echo "   请确认FRP是否正在运行"
fi
echo ""

# 日志检查
echo "📋 最近的Nginx日志..."
docker logs btc-watcher-nginx --tail 5 2>&1 | sed 's/^/   /'
echo ""

# WebSocket连接建议
echo "💡 WebSocket连接测试建议:"
echo "   1. 浏览器访问: http://47.108.221.231:60001"
echo "   2. 打开开发者工具 (F12) -> Network -> WS"
echo "   3. 登录系统，查看WebSocket连接状态"
echo "   4. 应该看到: ws://47.108.221.231:60001/api/v1/ws"
echo "   5. 状态应该是: 101 Switching Protocols"
echo ""

echo "📖 详细文档: cat FRP_WEBSOCKET_GUIDE.md"
echo "================================"
