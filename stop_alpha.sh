#!/bin/bash

# BTC Watcher Alpha测试环境停止脚本

echo "=========================================="
echo "BTC Watcher Alpha测试环境停止"
echo "=========================================="
echo ""

# 1. 停止Nginx
echo "【1】停止Nginx..."
docker stop btc-watcher-nginx 2>/dev/null && docker rm btc-watcher-nginx 2>/dev/null
echo "  ✓ Nginx已停止"
echo ""

# 2. 停止前端
echo "【2】停止前端服务..."
pkill -f "vite" 2>/dev/null
echo "  ✓ 前端服务已停止"
echo ""

# 3. 停止后端
echo "【3】停止后端API..."
pkill -f "uvicorn.*main:app" 2>/dev/null
echo "  ✓ 后端API已停止"
echo ""

# 4. 可选：停止PostgreSQL和Redis
read -p "是否停止PostgreSQL和Redis? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "【4】停止数据库服务..."
    docker stop btc-watcher-db-1 2>/dev/null
    docker stop btc-watcher-redis-1 2>/dev/null
    echo "  ✓ 数据库服务已停止"
else
    echo "  保持PostgreSQL和Redis运行"
fi

echo ""
echo "=========================================="
echo "✓ Alpha测试环境已停止"
echo "=========================================="
