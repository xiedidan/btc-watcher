#!/bin/bash

echo "🔄 Restarting Frontend Development Server..."

# 停止现有的Vite dev server
echo "Stopping existing Vite dev server..."
pkill -f "vite" || echo "No existing Vite process found"

# 等待进程完全停止
sleep 2

# 启动新的dev server
echo "Starting Vite dev server..."
cd /home/xd/project/btc-watcher/frontend
npm run dev &

echo "✅ Frontend dev server restarted"
echo "📱 Access the app at: http://localhost:3000"
echo "🔌 WebSocket will connect through Vite proxy to backend"
