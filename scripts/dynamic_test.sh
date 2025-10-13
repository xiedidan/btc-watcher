#!/bin/bash

# BTC Watcher 完整动态测试脚本
# Dynamic Testing Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED_TESTS++))
}

log_fail() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 测试函数
test_service() {
    local name=$1
    local command=$2
    ((TOTAL_TESTS++))

    echo -n "Testing $name... "
    if eval "$command" > /dev/null 2>&1; then
        log_success "$name"
        return 0
    else
        log_fail "$name"
        return 1
    fi
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         BTC Watcher 完整动态测试                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================
# 阶段 1: 启动服务
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 1: 启动Docker服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_info "停止现有容器..."
docker-compose down 2>&1 | grep -v "^$" || true

log_info "启动所有服务..."
docker-compose up -d

log_info "等待服务启动 (60秒)..."
for i in {60..1}; do
    echo -ne "\r等待中... $i 秒 "
    sleep 1
done
echo -e "\r${GREEN}等待完成！${NC}                "
echo ""

# ============================================
# 阶段 2: 容器状态检查
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 2: 容器状态检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_service "nginx容器运行" "docker ps | grep btc-watcher-nginx"
test_service "frontend容器运行" "docker ps | grep btc-watcher-web"
test_service "backend容器运行" "docker ps | grep btc-watcher-api"
test_service "数据库容器运行" "docker ps | grep btc-watcher-db"
test_service "Redis容器运行" "docker ps | grep btc-watcher-redis"
echo ""

# ============================================
# 阶段 3: 服务健康检查
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 3: 服务健康检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# PostgreSQL
test_service "PostgreSQL连接" "docker exec btc-watcher-db pg_isready -U btc_watcher"

# Redis
test_service "Redis连接" "docker exec btc-watcher-redis redis-cli ping | grep -q PONG"

# 等待后端完全启动
log_info "等待后端API完全启动 (30秒)..."
sleep 30

# Backend API
test_service "Backend健康检查" "curl -s -f http://localhost:8000/api/v1/system/health"
test_service "Backend API文档" "curl -s -f http://localhost:8000/docs"

# Frontend
test_service "Frontend可访问" "curl -s -f http://localhost"

# Nginx
test_service "Nginx健康检查" "curl -s -f http://localhost/health"
echo ""

# ============================================
# 阶段 4: API功能测试
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 4: API功能测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 用户注册
log_info "测试用户注册..."
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser_'$(date +%s)'",
    "email": "test'$(date +%s)'@example.com",
    "password": "test123456"
  }')
REGISTER_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
if [ "$REGISTER_CODE" = "200" ]; then
    ((TOTAL_TESTS++))
    log_success "用户注册API"
else
    ((TOTAL_TESTS++))
    log_fail "用户注册API (HTTP $REGISTER_CODE)"
fi

# 用户登录
log_info "测试用户登录 (admin账号)..."
LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")
LOGIN_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
if [ "$LOGIN_CODE" = "200" ]; then
    ((TOTAL_TESTS++))
    log_success "用户登录API"
    TOKEN=$(echo "$LOGIN_RESPONSE" | head -n-1 | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    log_info "获得访问令牌: ${TOKEN:0:20}..."
else
    ((TOTAL_TESTS++))
    log_fail "用户登录API (HTTP $LOGIN_CODE)"
    TOKEN=""
fi

# 系统容量查询
if [ -n "$TOKEN" ]; then
    log_info "测试系统容量查询..."
    CAPACITY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET http://localhost:8000/api/v1/system/capacity \
      -H "Authorization: Bearer $TOKEN")
    CAPACITY_CODE=$(echo "$CAPACITY_RESPONSE" | tail -n1)
    if [ "$CAPACITY_CODE" = "200" ]; then
        ((TOTAL_TESTS++))
        log_success "系统容量查询API"
        CAPACITY_DATA=$(echo "$CAPACITY_RESPONSE" | head -n-1)
        echo "   容量信息: $CAPACITY_DATA"
    else
        ((TOTAL_TESTS++))
        log_fail "系统容量查询API (HTTP $CAPACITY_CODE)"
    fi
fi

# 创建策略
if [ -n "$TOKEN" ]; then
    log_info "测试创建策略..."
    STRATEGY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/v1/strategies/ \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "测试策略_'$(date +%s)'",
        "strategy_class": "SampleStrategy",
        "exchange": "binance",
        "timeframe": "1h",
        "pair_whitelist": ["BTC/USDT"],
        "pair_blacklist": [],
        "dry_run": true,
        "dry_run_wallet": 1000,
        "stake_amount": null,
        "max_open_trades": 3,
        "signal_thresholds": {
          "strong": 0.8,
          "medium": 0.6,
          "weak": 0.4
        }
      }')
    STRATEGY_CODE=$(echo "$STRATEGY_RESPONSE" | tail -n1)
    if [ "$STRATEGY_CODE" = "200" ]; then
        ((TOTAL_TESTS++))
        log_success "创建策略API"
        STRATEGY_ID=$(echo "$STRATEGY_RESPONSE" | head -n-1 | grep -o '"id":[0-9]*' | cut -d':' -f2)
        log_info "创建的策略ID: $STRATEGY_ID"
    else
        ((TOTAL_TESTS++))
        log_fail "创建策略API (HTTP $STRATEGY_CODE)"
    fi
fi

# 获取策略列表
if [ -n "$TOKEN" ]; then
    log_info "测试获取策略列表..."
    STRATEGIES_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET http://localhost:8000/api/v1/strategies/ \
      -H "Authorization: Bearer $TOKEN")
    STRATEGIES_CODE=$(echo "$STRATEGIES_RESPONSE" | tail -n1)
    if [ "$STRATEGIES_CODE" = "200" ]; then
        ((TOTAL_TESTS++))
        log_success "获取策略列表API"
    else
        ((TOTAL_TESTS++))
        log_fail "获取策略列表API (HTTP $STRATEGIES_CODE)"
    fi
fi
echo ""

# ============================================
# 阶段 5: 数据库测试
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 5: 数据库测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查数据库表
log_info "检查数据库表结构..."
TABLES=$(docker exec btc-watcher-db psql -U btc_watcher -d btc_watcher -t -c "\dt" 2>/dev/null | grep -c "public" || echo "0")
((TOTAL_TESTS++))
if [ "$TABLES" -ge 7 ]; then
    log_success "数据库表结构 (找到 $TABLES 个表)"
else
    log_fail "数据库表结构 (只找到 $TABLES 个表，期望至少7个)"
fi

# 检查用户表
USERS=$(docker exec btc-watcher-db psql -U btc_watcher -d btc_watcher -t -c "SELECT COUNT(*) FROM users" 2>/dev/null || echo "0")
((TOTAL_TESTS++))
if [ "$USERS" -ge 1 ]; then
    log_success "用户数据 (找到 $USERS 个用户)"
else
    log_fail "用户数据 (找到 $USERS 个用户)"
fi
echo ""

# ============================================
# 阶段 6: 日志检查
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 6: 日志错误检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Backend错误日志
log_info "检查Backend错误日志..."
BACKEND_ERRORS=$(docker logs btc-watcher-api 2>&1 | grep -i "error" | grep -v "INFO" | wc -l || echo "0")
((TOTAL_TESTS++))
if [ "$BACKEND_ERRORS" -lt 5 ]; then
    log_success "Backend日志 ($BACKEND_ERRORS 个错误)"
else
    log_warning "Backend日志 (发现 $BACKEND_ERRORS 个错误，请检查)"
fi

# Nginx错误日志
log_info "检查Nginx错误日志..."
NGINX_ERRORS=$(docker logs btc-watcher-nginx 2>&1 | grep -i "error" | wc -l || echo "0")
((TOTAL_TESTS++))
if [ "$NGINX_ERRORS" -lt 5 ]; then
    log_success "Nginx日志 ($NGINX_ERRORS 个错误)"
else
    log_warning "Nginx日志 (发现 $NGINX_ERRORS 个错误，请检查)"
fi
echo ""

# ============================================
# 阶段 7: 性能测试
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "阶段 7: 性能测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# API响应时间
log_info "测试API响应时间..."
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/api/v1/system/health)
RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc | cut -d'.' -f1)
((TOTAL_TESTS++))
if [ "$RESPONSE_MS" -lt 1000 ]; then
    log_success "API响应时间 (${RESPONSE_MS}ms)"
else
    log_warning "API响应时间较慢 (${RESPONSE_MS}ms)"
fi

# 前端响应时间
log_info "测试前端响应时间..."
FRONTEND_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost)
FRONTEND_MS=$(echo "$FRONTEND_TIME * 1000" | bc | cut -d'.' -f1)
((TOTAL_TESTS++))
if [ "$FRONTEND_MS" -lt 2000 ]; then
    log_success "前端响应时间 (${FRONTEND_MS}ms)"
else
    log_warning "前端响应时间较慢 (${FRONTEND_MS}ms)"
fi
echo ""

# ============================================
# 测试总结
# ============================================
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    测试结果总结                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"

SUCCESS_RATE=$(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)
echo -e "成功率: ${GREEN}${SUCCESS_RATE}%${NC}"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🎉 所有测试通过！系统运行正常！                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "访问地址:"
    echo "  - 前端: http://localhost"
    echo "  - API文档: http://localhost:8000/docs"
    echo "  - 默认登录: admin / admin123"
    echo ""
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  部分测试失败，请检查日志                                 ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "查看日志:"
    echo "  docker-compose logs -f"
    echo ""
    exit 1
fi
