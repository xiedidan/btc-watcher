#!/bin/bash

# BTC Watcher 停止脚本

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

# 停止服务
stop_services() {
    log_info "停止BTC Watcher服务..."

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        if docker-compose ps -q | grep -q .; then
            docker-compose down
            log_success "服务已停止"
        else
            log_info "没有运行中的服务"
        fi
    else
        if docker compose ps -q | grep -q .; then
            docker compose down
            log_success "服务已停止"
        else
            log_info "没有运行中的服务"
        fi
    fi
}

# 显示停止后状态
show_status() {
    log_info "检查服务状态..."

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        local running_containers=$(docker-compose ps -q)
    else
        local running_containers=$(docker compose ps -q)
    fi

    if [ -z "$running_containers" ]; then
        log_success "所有服务已停止"
    else
        log_warning "仍有运行中的容器:"
        if command -v docker-compose &> /dev/null; then
            docker-compose ps
        else
            docker compose ps
        fi
    fi
}

# 清理选项
cleanup_options() {
    echo
    log_info "清理选项:"
    echo "1. 保留数据，仅停止服务 (默认)"
    echo "2. 停止服务并删除容器"
    echo "3. 停止服务，删除容器和网络"
    echo "4. 完全清理 (包括数据卷，谨慎使用)"
    echo

    read -p "请选择清理级别 (1-4, 默认1): " -n 1 -r cleanup_level
    echo

    case $cleanup_level in
        2)
            log_info "删除容器..."
            cd "$PROJECT_DIR"
            if command -v docker-compose &> /dev/null; then
                docker-compose down --remove-orphans
            else
                docker compose down --remove-orphans
            fi
            ;;
        3)
            log_info "删除容器和网络..."
            cd "$PROJECT_DIR"
            if command -v docker-compose &> /dev/null; then
                docker-compose down --remove-orphans --networks
            else
                docker compose down --remove-orphans
            fi
            ;;
        4)
            log_warning "警告: 这将删除所有数据!"
            read -p "确认删除所有数据? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                log_info "完全清理..."
                cd "$PROJECT_DIR"
                if command -v docker-compose &> /dev/null; then
                    docker-compose down --remove-orphans --volumes
                else
                    docker compose down --remove-orphans --volumes
                fi

                # 删除数据目录
                log_info "删除数据目录..."
                rm -rf "$PROJECT_DIR/data"
                log_warning "所有数据已删除"
            else
                log_info "取消完全清理"
            fi
            ;;
        *)
            log_info "仅停止服务，保留所有数据"
            ;;
    esac
}

# 主函数
main() {
    echo "================================"
    echo "    BTC Watcher 停止脚本"
    echo "================================"
    echo

    # 检查是否有服务在运行
    cd "$PROJECT_DIR"
    local has_running_services=false

    if command -v docker-compose &> /dev/null; then
        if docker-compose ps -q | grep -q .; then
            has_running_services=true
        fi
    else
        if docker compose ps -q 2>/dev/null | grep -q .; then
            has_running_services=true
        fi
    fi

    if [ "$has_running_services" = false ]; then
        log_info "没有运行中的BTC Watcher服务"
        exit 0
    fi

    # 显示当前运行的服务
    log_info "当前运行的服务:"
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    echo
    read -p "是否停止所有服务? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        stop_services
        show_status

        # 提供清理选项
        cleanup_options

        echo
        log_success "BTC Watcher 已停止"
        log_info "使用 './scripts/start.sh' 重新启动服务"
    else
        log_info "取消停止操作"
    fi
}

# 如果脚本被直接执行（而不是被source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi