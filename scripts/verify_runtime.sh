#!/bin/bash

# BTC Watcher Runtime Verification Script
# 运行时验证脚本 - 检查所有服务是否正常运行

set -e

echo "=================================================="
echo "🚀 BTC Watcher Runtime Verification"
echo "=================================================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Test function
test_service() {
    local name=$1
    local command=$2

    echo -n "🔍 Testing $name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

# 1. Check Docker
echo ""
echo "📦 Checking Docker..."
test_service "Docker installed" "docker --version"
test_service "Docker running" "docker ps"

# 2. Check Docker Compose
echo ""
echo "📦 Checking Docker Compose..."
test_service "Docker Compose installed" "docker-compose --version || docker compose version"

# 3. Check containers
echo ""
echo "🐳 Checking Containers..."
test_service "Backend container" "docker ps | grep btc-watcher-backend"
test_service "Frontend container" "docker ps | grep btc-watcher-frontend"
test_service "Database container" "docker ps | grep btc-watcher-db"
test_service "Redis container" "docker ps | grep btc-watcher-redis"
test_service "Nginx container" "docker ps | grep btc-watcher-nginx"

# 4. Check services are responding
echo ""
echo "🌐 Checking Service Endpoints..."

# Wait a moment for services to be ready
sleep 2

# Check backend health
echo -n "🔍 Testing Backend API (http://localhost:8000/api/v1/system/health)... "
if curl -s -f http://localhost:8000/api/v1/system/health > /dev/null; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    echo -e "${YELLOW}   Tip: Backend may still be starting up. Wait a few seconds and try again.${NC}"
    ((FAILED++))
fi

# Check frontend
echo -n "🔍 Testing Frontend (http://localhost)... "
if curl -s -f http://localhost > /dev/null; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAILED++))
fi

# Check Swagger docs
echo -n "🔍 Testing API Documentation (http://localhost:8000/docs)... "
if curl -s -f http://localhost:8000/docs > /dev/null; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAILED++))
fi

# 5. Check database connection
echo ""
echo "💾 Checking Database..."
echo -n "🔍 Testing PostgreSQL connection... "
if docker exec btc-watcher-db pg_isready -U btc_watcher > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAILED++))
fi

# 6. Check Redis
echo ""
echo "📮 Checking Redis..."
echo -n "🔍 Testing Redis connection... "
if docker exec btc-watcher-redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAILED++))
fi

# 7. Check logs for errors
echo ""
echo "📝 Checking Logs for Errors..."
echo -n "🔍 Checking backend logs... "
ERROR_COUNT=$(docker logs btc-watcher-backend 2>&1 | grep -i "error" | grep -v "INFO" | wc -l || echo 0)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC} (No errors found)"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  WARNING${NC} (Found $ERROR_COUNT potential errors)"
    echo "   Run 'docker logs btc-watcher-backend' to investigate"
fi

# Summary
echo ""
echo "=================================================="
echo "📊 Verification Summary"
echo "=================================================="
TOTAL=$((PASSED + FAILED))
PERCENTAGE=$((PASSED * 100 / TOTAL))

echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo -e "Total:  $TOTAL"
echo -e "Success Rate: ${GREEN}${PERCENTAGE}%${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All checks passed! Your BTC Watcher deployment is healthy.${NC}"
    echo ""
    echo "📍 Access Points:"
    echo "   - Frontend:        http://localhost"
    echo "   - Backend API:     http://localhost:8000"
    echo "   - API Docs:        http://localhost:8000/docs"
    echo "   - ReDoc:           http://localhost:8000/redoc"
    echo ""
    echo "🔐 Default Login:"
    echo "   - Username: admin"
    echo "   - Password: admin123"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}⚠️  Some checks failed. Please review the output above.${NC}"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check if all containers are running: docker ps"
    echo "   2. Check logs: docker-compose logs"
    echo "   3. Restart services: docker-compose restart"
    echo ""
    exit 1
fi
