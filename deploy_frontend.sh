#!/bin/bash

# BTC Watcher 前端更新部署脚本
# 用于前端代码变更后的快速部署

echo "=========================================="
echo "   前端更新部署"
echo "=========================================="
echo ""

PROJECT_DIR="/home/xd/project/btc-watcher"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# 1. 检查是否在项目目录
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ 错误: 前端目录不存在: $FRONTEND_DIR"
    exit 1
fi

# 2. 停止现有前端服务
echo "【1】停止现有前端服务..."
pkill -f "vite" 2>/dev/null || echo "  ℹ️  没有运行中的Vite进程"
sleep 2

# 检查是否还有残留进程
if lsof -i :3000 > /dev/null 2>&1; then
    echo "  ⚠️  端口3000仍被占用，强制释放..."
    PID=$(lsof -ti :3000)
    kill -9 $PID 2>/dev/null
    sleep 1
fi

echo "  ✅ 前端服务已停止"
echo ""

# 3. 进入前端目录
cd "$FRONTEND_DIR"

# 4. （可选）安装/更新依赖
read -p "是否需要更新依赖包? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "【2】更新依赖包..."
    npm install
    echo "  ✅ 依赖包更新完成"
    echo ""
else
    echo "【2】跳过依赖包更新"
    echo ""
fi

# 5. （可选）清理缓存
read -p "是否清理Vite缓存? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "【3】清理Vite缓存..."
    rm -rf .vite node_modules/.vite
    echo "  ✅ 缓存已清理"
    echo ""
else
    echo "【3】保留缓存"
    echo ""
fi

# 6. 启动前端服务
echo "【4】启动前端服务..."

# 方式1: 后台运行（默认）
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "  🚀 前端服务已启动 (PID: $FRONTEND_PID)"
echo ""

# 7. 等待服务就绪
echo "【5】等待服务就绪..."
sleep 5

MAX_RETRY=10
RETRY=0
while [ $RETRY -lt $MAX_RETRY ]; do
    if curl -s -I http://localhost:3000 > /dev/null 2>&1; then
        echo "  ✅ 前端服务就绪"
        break
    fi
    echo "  ⏳ 等待服务启动... ($((RETRY+1))/$MAX_RETRY)"
    sleep 2
    RETRY=$((RETRY+1))
done

if [ $RETRY -eq $MAX_RETRY ]; then
    echo "  ❌ 前端服务启动超时"
    echo ""
    echo "  查看日志:"
    echo "  tail -50 /tmp/frontend.log"
    exit 1
fi

echo ""

# 8. 验证服务
echo "【6】验证服务状态..."

# 检查进程
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "  ✅ 进程运行正常 (PID: $FRONTEND_PID)"
else
    echo "  ❌ 进程已退出，请查看日志"
    echo "  tail -50 /tmp/frontend.log"
    exit 1
fi

# 检查HTTP响应
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    echo "  ✅ HTTP响应正常 (状态码: $HTTP_STATUS)"
else
    echo "  ⚠️  HTTP响应异常 (状态码: $HTTP_STATUS)"
fi

# 检查Nginx代理
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "  ✅ Nginx代理正常"
else
    echo "  ⚠️  Nginx代理可能有问题"
    echo "  运行: docker restart btc-watcher-nginx"
fi

echo ""

# 9. 完成
echo "=========================================="
echo "✅ 前端更新部署完成！"
echo ""
echo "访问地址:"
echo "  前端直接访问: http://localhost:3000"
echo "  通过Nginx访问: http://localhost:8501"
echo ""
echo "实用命令:"
echo "  查看日志: tail -f /tmp/frontend.log"
echo "  停止服务: pkill -f vite"
echo "  重启服务: ./deploy_frontend.sh"
echo "  健康检查: ./check_health.sh"
echo ""
echo "💡 提示: 浏览器访问后按 Ctrl+Shift+R 强制刷新缓存"
echo "=========================================="
