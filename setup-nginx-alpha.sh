#!/bin/bash
# BTC Watcher Alpha Environment - Nginx Setup Script
# 用于配置Nginx反向代理8501端口到前端3000端口

set -e

echo "========================================="
echo "BTC Watcher Nginx Setup for Alpha Environment"
echo "========================================="
echo ""

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo "请使用sudo运行此脚本:"
    echo "sudo bash $0"
    exit 1
fi

# 1. 安装Nginx
echo "Step 1: 安装Nginx..."
if ! command -v nginx &> /dev/null; then
    apt-get update
    apt-get install -y nginx
    echo "✓ Nginx安装成功"
else
    echo "✓ Nginx已安装"
fi

# 2. 复制配置文件
echo ""
echo "Step 2: 配置Nginx..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp "$SCRIPT_DIR/nginx/btc-watcher-alpha.conf" /etc/nginx/sites-available/

# 3. 创建软链接
if [ -f /etc/nginx/sites-enabled/btc-watcher-alpha.conf ]; then
    rm /etc/nginx/sites-enabled/btc-watcher-alpha.conf
fi
ln -s /etc/nginx/sites-available/btc-watcher-alpha.conf /etc/nginx/sites-enabled/
echo "✓ 配置文件已部署"

# 4. 测试配置
echo ""
echo "Step 3: 测试Nginx配置..."
nginx -t

# 5. 重启Nginx
echo ""
echo "Step 4: 重启Nginx..."
systemctl restart nginx
systemctl enable nginx
echo "✓ Nginx已重启并设置为开机自启"

# 6. 检查端口
echo ""
echo "Step 5: 检查端口状态..."
echo "前端端口(3000):"
lsof -i :3000 | grep LISTEN || echo "  ⚠ 前端未运行在3000端口"
echo "后端端口(8000):"
lsof -i :8000 | grep LISTEN || echo "  ⚠ 后端未运行在8000端口"
echo "Nginx代理端口(8501):"
lsof -i :8501 | grep LISTEN || echo "  ✗ Nginx未监听8501端口"

# 7. 显示防火墙提示
echo ""
echo "========================================="
echo "配置完成！"
echo "========================================="
echo ""
echo "访问地址:"
echo "  - 本地: http://localhost:8501"
echo "  - 局域网: http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "如需外网访问，请确保:"
echo "  1. 防火墙开放8501端口: sudo ufw allow 8501"
echo "  2. FRP配置映射8501端口"
echo ""
echo "查看Nginx日志:"
echo "  - 访问日志: tail -f /var/log/nginx/btc-watcher-access.log"
echo "  - 错误日志: tail -f /var/log/nginx/btc-watcher-error.log"
echo ""
