#!/bin/bash

# BTC Watcher 启动脚本

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖项..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或未在PATH中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或未在PATH中"
        exit 1
    fi

    log_success "依赖项检查完成"
}

# 检查环境文件
check_env_file() {
    log_info "检查环境配置文件..."

    if [ ! -f "$PROJECT_DIR/.env" ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            log_warning ".env 文件不存在，正在从 .env.example 复制..."
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            log_warning "请编辑 .env 文件配置必要的环境变量"
        else
            log_error ".env 和 .env.example 文件都不存在"
            exit 1
        fi
    fi

    log_success "环境配置文件检查完成"
}

# 创建必要的数据目录
create_directories() {
    log_info "创建数据目录..."

    local dirs=(
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
        mkdir -p "$PROJECT_DIR/$dir"
    done

    log_success "数据目录创建完成"
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用..."

    local ports=(80 443 5432 6379 8080 8081)
    local occupied_ports=()

    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            occupied_ports+=($port)
        elif ss -tuln 2>/dev/null | grep -q ":$port "; then
            occupied_ports+=($port)
        fi
    done

    if [ ${#occupied_ports[@]} -gt 0 ]; then
        log_warning "以下端口已被占用: ${occupied_ports[*]}"
        log_warning "这可能会导致服务启动失败"
        read -p "是否继续启动? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "用户取消启动"
            exit 0
        fi
    fi

    log_success "端口检查完成"
}

# 拉取镜像
pull_images() {
    log_info "拉取Docker镜像..."

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        docker-compose pull
    else
        docker compose pull
    fi

    log_success "镜像拉取完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    cd "$PROJECT_DIR"

    # 启动核心服务
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d db redis
    else
        docker compose up -d db redis
    fi

    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 10

    # 启动应用服务
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi

    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."

    # 检查API服务
    local api_ready=false
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ] && [ "$api_ready" = false ]; do
        if curl -s http://localhost/api/v1/health &>/dev/null; then
            api_ready=true
        else
            log_info "等待API服务启动... ($attempt/$max_attempts)"
            sleep 2
            ((attempt++))
        fi
    done

    if [ "$api_ready" = true ]; then
        log_success "API服务已就绪"
    else
        log_warning "API服务启动可能存在问题，请检查日志"
    fi
}

# 显示服务状态
show_status() {
    log_info "服务状态:"

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    echo
    log_info "访问地址:"
    echo "  Web UI: http://localhost"
    echo "  API 文档: http://localhost/api/v1/docs"
    echo "  数据库管理 (调试模式): http://localhost:8080"
    echo "  Redis管理 (调试模式): http://localhost:8081"
    echo
    log_info "日志查看命令:"
    echo "  所有服务: docker-compose logs -f"
    echo "  特定服务: docker-compose logs -f <service_name>"
}

# 主函数
main() {
    echo "================================"
    echo "    BTC Watcher 启动脚本"
    echo "================================"
    echo

    check_dependencies
    check_env_file
    create_directories
    check_ports
    pull_images
    start_services
    wait_for_services
    show_status

    echo
    log_success "BTC Watcher 启动完成!"
    log_info "使用 './scripts/stop.sh' 停止服务"
    log_info "使用 './scripts/logs.sh' 查看日志"
}

# 如果脚本被直接执行（而不是被source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi