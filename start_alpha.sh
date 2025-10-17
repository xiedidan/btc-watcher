#!/bin/bash

# BTC Watcher Alpha测试环境启动脚本
# 统一对外端口: 8501

echo "=========================================="
echo "BTC Watcher Alpha测试环境启动"
echo "=========================================="
echo ""

# 检查服务状态
check_service() {
    local name=$1
    local port=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        echo "✓ $name 已在端口 $port 运行"
        return 0
    else
        echo "✗ $name 未运行 (端口 $port)"
        return 1
    fi
}

# 1. 检查PostgreSQL
echo "【1】检查PostgreSQL..."
if check_service "PostgreSQL" 5432; then
    :
else
    echo "  启动PostgreSQL容器..."
    docker start btc-watcher-db-1 2>/dev/null || \
    docker-compose up -d db
fi
echo ""

# 2. 检查Redis
echo "【2】检查Redis..."
if check_service "Redis" 6379; then
    :
else
    echo "  启动Redis容器..."
    docker start btc-watcher-redis-1 2>/dev/null || \
    cd /home/xd/project/btc-watcher && docker-compose up -d redis
fi
echo ""

# 3. 启动后端API (端口8000)
echo "【3】检查后端API..."
if check_service "后端API" 8000; then
    :
else
    echo "  启动后端API (端口8000)..."
    cd /home/xd/project/btc-watcher/backend
    source venv/bin/activate
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
    sleep 3
fi
echo ""

# 4. 启动前端 (端口3000)
echo "【4】检查前端服务..."
if check_service "前端服务" 3000; then
    :
else
    echo "  启动前端服务 (端口3000)..."
    cd /home/xd/project/btc-watcher/frontend
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    sleep 5
fi
echo ""

# 5. 启动Nginx (端口8501)
echo "【5】检查Nginx反向代理..."
if docker ps | grep btc-watcher-nginx > /dev/null; then
    echo "✓ Nginx 已运行"
else
    echo "  启动Nginx (端口8501)..."
    docker rm -f btc-watcher-nginx 2>/dev/null
    docker run -d --name btc-watcher-nginx \
      --add-host=host.docker.internal:host-gateway \
      -p 8501:8501 \
      -v /home/xd/project/btc-watcher/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
      nginx:alpine
    sleep 2
fi
echo ""

# 验证所有服务
echo "=========================================="
echo "服务状态验证"
echo "=========================================="

ALL_OK=true

if check_service "PostgreSQL" 5432; then :; else ALL_OK=false; fi
if check_service "Redis" 6379; then :; else ALL_OK=false; fi
if check_service "后端API" 8000; then :; else ALL_OK=false; fi
if check_service "前端服务" 3000; then :; else ALL_OK=false; fi

echo ""
echo "【Nginx状态】"
if docker ps | grep btc-watcher-nginx > /dev/null; then
    echo "✓ Nginx反向代理运行中 (端口8501)"
else
    echo "✗ Nginx反向代理未运行"
    ALL_OK=false
fi

echo ""
echo "=========================================="

if $ALL_OK; then
    echo "✓ 所有服务启动成功！"
    echo ""
    echo "访问地址:"
    echo "  主应用:   http://localhost:8501/"
    echo "  API文档:  http://localhost:8501/docs"
    echo "  健康检查: http://localhost:8501/health"
    echo ""
    echo "测试账号: alpha1 / Alpha@2025"
    echo "详细信息: 查看 ALPHA_TEST_GUIDE.md"
else
    echo "✗ 部分服务启动失败，请检查日志"
    echo ""
    echo "日志位置:"
    echo "  后端: /tmp/backend.log"
    echo "  前端: /tmp/frontend.log"
    echo "  Nginx: docker logs btc-watcher-nginx"
fi

echo "=========================================="
