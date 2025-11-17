#!/bin/bash

# BTC Watcher 后端更新部署脚本
# 用于后端代码变更后的快速部署

echo "=========================================="
echo "   后端更新部署"
echo "=========================================="
echo ""

PROJECT_DIR="/home/xd/project/btc-watcher"
BACKEND_DIR="$PROJECT_DIR/backend"

# 1. 检查是否在项目目录
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ 错误: 后端目录不存在: $BACKEND_DIR"
    exit 1
fi

# 2. 停止现有后端服务
echo "【1】停止现有后端服务..."
pkill -f "uvicorn.*main:app" 2>/dev/null || echo "  ℹ️  没有运行中的Uvicorn进程"
sleep 2

# 检查是否还有残留进程
if lsof -i :8000 > /dev/null 2>&1; then
    echo "  ⚠️  端口8000仍被占用，强制释放..."
    PID=$(lsof -ti :8000)
    kill -9 $PID 2>/dev/null
    sleep 1
fi

echo "  ✅ 后端服务已停止"
echo ""

# 3. 进入后端目录
cd "$BACKEND_DIR"

# 4. 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 错误: 虚拟环境不存在"
    echo "  请先运行: python -m venv venv"
    exit 1
fi

source venv/bin/activate

# 5. （可选）更新依赖
read -p "是否需要更新依赖包? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "【2】更新依赖包..."
    pip install -r requirements.txt
    echo "  ✅ 依赖包更新完成"
    echo ""
else
    echo "【2】跳过依赖包更新"
    echo ""
fi

# 6. （可选）数据库迁移
read -p "是否需要运行数据库迁移? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "【3】运行数据库迁移..."

    # 检查是否有待迁移
    PENDING=$(alembic current 2>&1)
    echo "  当前版本: $PENDING"

    # 执行迁移
    alembic upgrade head

    if [ $? -eq 0 ]; then
        echo "  ✅ 数据库迁移完成"
    else
        echo "  ❌ 数据库迁移失败"
        deactivate
        exit 1
    fi
    echo ""
else
    echo "【3】跳过数据库迁移"
    echo ""
fi

# 7. 启动后端服务
echo "【4】启动后端服务..."

# 清理旧日志
mv /tmp/backend_new.log /tmp/backend_new.log.old 2>/dev/null

# 启动服务（--reload模式用于开发）
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &
BACKEND_PID=$!

echo "  🚀 后端服务已启动 (PID: $BACKEND_PID)"
echo ""

# 8. 等待服务就绪
echo "【5】等待服务就绪..."
sleep 5

MAX_RETRY=15
RETRY=0
while [ $RETRY -lt $MAX_RETRY ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✅ 后端服务就绪"
        break
    fi

    # 检查进程是否还在运行
    if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "  ❌ 后端进程已退出，请查看日志"
        echo ""
        echo "  最近的错误:"
        tail -20 /tmp/backend_new.log | grep -E "ERROR|Exception" || tail -20 /tmp/backend_new.log
        deactivate
        exit 1
    fi

    echo "  ⏳ 等待服务启动... ($((RETRY+1))/$MAX_RETRY)"
    sleep 2
    RETRY=$((RETRY+1))
done

if [ $RETRY -eq $MAX_RETRY ]; then
    echo "  ❌ 后端服务启动超时"
    echo ""
    echo "  查看日志:"
    echo "  tail -50 /tmp/backend_new.log"
    deactivate
    exit 1
fi

echo ""

# 9. 验证服务
echo "【6】验证服务状态..."

# 检查进程
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "  ✅ 进程运行正常 (PID: $BACKEND_PID)"
else
    echo "  ❌ 进程已退出，请查看日志"
    echo "  tail -50 /tmp/backend_new.log"
    deactivate
    exit 1
fi

# 检查健康检查
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "  ✅ 健康检查通过"
    VERSION=$(echo "$HEALTH_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null)
    ENV=$(echo "$HEALTH_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('environment', 'unknown'))" 2>/dev/null)
    echo "  📌 版本: $VERSION"
    echo "  📌 环境: $ENV"
else
    echo "  ⚠️  健康检查异常"
    echo "  响应: $HEALTH_RESPONSE"
fi

# 检查API文档
if curl -s -I http://localhost:8000/docs | grep -q "200"; then
    echo "  ✅ API文档可访问"
else
    echo "  ⚠️  API文档无法访问"
fi

# 检查Nginx代理
if curl -s http://localhost:8501/health > /dev/null 2>&1; then
    echo "  ✅ Nginx代理正常"
else
    echo "  ⚠️  Nginx代理可能有问题"
    echo "  运行: docker restart btc-watcher-nginx"
fi

echo ""

# 10. 完成
echo "=========================================="
echo "✅ 后端更新部署完成！"
echo ""
echo "访问地址:"
echo "  健康检查: http://localhost:8000/health"
echo "  API文档:  http://localhost:8000/docs"
echo "  通过Nginx: http://localhost:8501/docs"
echo ""
echo "实用命令:"
echo "  查看日志: tail -f /tmp/backend_new.log"
echo "  停止服务: pkill -f 'uvicorn.*main:app'"
echo "  重启服务: ./deploy_backend.sh"
echo "  健康检查: ./check_health.sh"
echo ""
echo "💡 提示: --reload模式已启用，代码变更会自动重载"
echo "=========================================="

deactivate
