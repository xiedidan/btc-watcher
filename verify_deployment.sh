#!/bin/bash

# BTC Watcher 部署验证脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "================================"
echo "   BTC Watcher 部署验证"
echo "================================"
echo

# 1. 检查Docker
log_info "检查 Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_success "Docker 已安装: $DOCKER_VERSION"

    # 检查Docker服务状态
    if systemctl is-active --quiet docker 2>/dev/null || docker info &>/dev/null; then
        log_success "Docker 服务运行正常"
    else
        log_error "Docker 服务未运行"
        exit 1
    fi
else
    log_error "Docker 未安装"
    exit 1
fi

# 2. 检查Docker Compose
log_info "检查 Docker Compose..."
COMPOSE_CMD=""
if command -v docker-compose &> /dev/null && docker-compose --version &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    COMPOSE_VERSION=$(docker-compose --version)
    log_success "Docker Compose 已安装: $COMPOSE_VERSION"
elif command -v ~/.local/bin/docker-compose &> /dev/null; then
    COMPOSE_CMD="~/.local/bin/docker-compose"
    COMPOSE_VERSION=$(~/.local/bin/docker-compose --version)
    log_success "Docker Compose 已安装 (本地): $COMPOSE_VERSION"
elif docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
    COMPOSE_VERSION=$(docker compose version)
    log_success "Docker Compose Plugin 可用: $COMPOSE_VERSION"
else
    log_error "Docker Compose 不可用"
    exit 1
fi

# 3. 检查项目文件
log_info "检查项目文件..."
required_files=(
    "docker-compose.yml"
    ".env.example"
    "scripts/start.sh"
    "scripts/stop.sh"
    "scripts/logs.sh"
)

for file in "${required_files[@]}"; do
    if [ -f "$PROJECT_DIR/$file" ]; then
        log_success "文件存在: $file"
    else
        log_error "文件缺失: $file"
        exit 1
    fi
done

# 4. 检查环境配置
log_info "检查环境配置..."
if [ -f "$PROJECT_DIR/.env" ]; then
    log_success ".env 文件存在"
else
    log_warning ".env 文件不存在，将从 .env.example 复制"
    if cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"; then
        log_success ".env 文件已创建"
    else
        log_error "无法创建 .env 文件"
        exit 1
    fi
fi

# 5. 检查端口占用
log_info "检查端口占用..."
ports=(80 443 5432 6379 8080 8081)
occupied_ports=()

for port in "${ports[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        occupied_ports+=($port)
    fi
done

if [ ${#occupied_ports[@]} -gt 0 ]; then
    log_warning "以下端口已被占用: ${occupied_ports[*]}"
    log_warning "启动时可能会出现端口冲突"
else
    log_success "所有必需端口都可用"
fi

# 6. 检查Docker镜像
log_info "检查Docker镜像..."
cd "$PROJECT_DIR"

# 验证docker-compose.yml语法
if eval "$COMPOSE_CMD config" &>/dev/null; then
    log_success "docker-compose.yml 语法正确"
else
    log_error "docker-compose.yml 语法错误"
    exit 1
fi

# 7. 创建数据目录
log_info "创建必要的数据目录..."
dirs=(
    "data/postgres"
    "data/redis"
    "data/logs/nginx"
    "data/logs/api"
    "data/logs/web"
    "data/logs/freqtrade"
    "data/logs/notification"
    "data/signals"
    "data/strategies"
)

for dir in "${dirs[@]}"; do
    if mkdir -p "$PROJECT_DIR/$dir"; then
        log_success "目录已创建: $dir"
    else
        log_error "无法创建目录: $dir"
        exit 1
    fi
done

# 8. 显示部署命令
echo
log_info "部署验证完成！可以使用以下命令："
echo "  启动服务: ./scripts/start.sh"
echo "  停止服务: ./scripts/stop.sh"
echo "  查看日志: ./scripts/logs.sh"
echo "  手动启动: $COMPOSE_CMD up -d"
echo
log_info "使用的Docker Compose命令: $COMPOSE_CMD"
echo
log_success "BTC Watcher 项目部署环境验证通过！"