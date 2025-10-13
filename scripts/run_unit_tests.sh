#!/bin/bash

# 单元测试运行脚本（使用虚拟环境）
# Unit Test Runner with Virtual Environment

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            BTC Watcher 单元测试运行器（venv）                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 进入backend目录
cd "$(dirname "$0")/../backend" || exit 1

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查并安装依赖
echo "📦 检查并安装依赖..."
pip install -q --upgrade pip

# 安装主要依赖
if [ -f "requirements.txt" ]; then
    echo "   安装主要依赖..."
    pip install -q -r requirements.txt
fi

# 安装测试依赖
if [ -f "requirements-test.txt" ]; then
    echo "   安装测试依赖..."
    pip install -q -r requirements-test.txt
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 运行单元测试..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 运行测试并生成报告
python -m pytest tests/unit/ \
    -v \
    --tb=short \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html \
    -p no:warnings \
    "$@"

TEST_RESULT=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ 所有单元测试通过！"
    echo ""
    echo "📊 测试覆盖率报告已生成: htmlcov/index.html"
else
    echo "❌ 部分测试失败，请检查上方输出"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $TEST_RESULT
