#!/bin/bash

# BTC Watcher 服务健康检查脚本
# 快速检查所有服务是否正常运行

echo "=========================================="
echo "   BTC Watcher 服务健康检查"
echo "=========================================="
echo ""

ALL_OK=true

# 1. PostgreSQL
echo "【1】PostgreSQL数据库"
if docker ps | grep btc-watcher-db-1 > /dev/null 2>&1; then
    echo "  ✅ 容器运行中"
    if PGPASSWORD=btc_watcher_password psql -h localhost -U btc_watcher_user -d btc_watcher -c "SELECT 1;" > /dev/null 2>&1; then
        echo "  ✅ 数据库连接正常"
    else
        echo "  ❌ 数据库无法连接"
        ALL_OK=false
    fi
else
    echo "  ❌ 容器未运行"
    ALL_OK=false
fi
echo ""

# 2. Redis
echo "【2】Redis缓存"
if docker ps | grep btc-watcher-redis-1 > /dev/null 2>&1; then
    echo "  ✅ 容器运行中"
    if redis-cli ping > /dev/null 2>&1; then
        echo "  ✅ Redis响应正常"
    else
        echo "  ❌ Redis无法连接"
        ALL_OK=false
    fi
else
    echo "  ❌ 容器未运行"
    ALL_OK=false
fi
echo ""

# 3. 后端API
echo "【3】后端API服务 (端口8000)"
if lsof -i :8000 > /dev/null 2>&1; then
    echo "  ✅ 进程运行中"
    HEALTH_CHECK=$(curl -s http://localhost:8000/health 2>&1)
    if echo "$HEALTH_CHECK" | grep -q "healthy"; then
        echo "  ✅ 健康检查通过"
        VERSION=$(echo "$HEALTH_CHECK" | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null)
        echo "  📌 版本: $VERSION"
    else
        echo "  ❌ 健康检查失败"
        ALL_OK=false
    fi
else
    echo "  ❌ 服务未运行"
    ALL_OK=false
fi
echo ""

# 4. 前端服务
echo "【4】前端服务 (端口3000)"
if lsof -i :3000 > /dev/null 2>&1; then
    echo "  ✅ 进程运行中"
    if curl -s -I http://localhost:3000 2>&1 | head -1 | grep -q "200\|301\|302"; then
        echo "  ✅ HTTP响应正常"
    else
        echo "  ⚠️  HTTP响应异常"
        ALL_OK=false
    fi
else
    echo "  ❌ 服务未运行"
    ALL_OK=false
fi
echo ""

# 5. Nginx反向代理
echo "【5】Nginx反向代理 (端口8501)"
if docker ps | grep btc-watcher-nginx > /dev/null 2>&1; then
    echo "  ✅ 容器运行中"
    if curl -s http://localhost:8501/health > /dev/null 2>&1; then
        echo "  ✅ 代理工作正常"
        echo "  🌐 访问地址: http://localhost:8501"
    else
        echo "  ❌ 代理无法访问"
        ALL_OK=false
    fi
else
    echo "  ❌ 容器未运行"
    ALL_OK=false
fi
echo ""

# 6. 磁盘空间
echo "【6】系统资源"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo "  ✅ 磁盘使用率: ${DISK_USAGE}%"
else
    echo "  ⚠️  磁盘使用率较高: ${DISK_USAGE}%"
fi

MEM_AVAILABLE=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAILABLE" -gt 1000 ]; then
    echo "  ✅ 可用内存: ${MEM_AVAILABLE}MB"
else
    echo "  ⚠️  可用内存较低: ${MEM_AVAILABLE}MB"
fi
echo ""

# 总结
echo "=========================================="
if $ALL_OK; then
    echo "✅ 所有服务运行正常！"
    echo ""
    echo "快速访问:"
    echo "  主应用:   http://localhost:8501"
    echo "  API文档:  http://localhost:8501/docs"
    echo "  健康检查: http://localhost:8501/health"
else
    echo "❌ 部分服务存在问题，请查看上述详情"
    echo ""
    echo "故障排查:"
    echo "  后端日志: tail -f /tmp/backend_new.log"
    echo "  前端日志: tail -f /tmp/frontend.log"
    echo "  Nginx日志: docker logs btc-watcher-nginx"
    echo ""
    echo "重启服务:"
    echo "  完整重启: ./start_alpha.sh"
    echo "  前端重启: ./restart-frontend.sh"
fi
echo "=========================================="
