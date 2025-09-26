#!/bin/bash

# BTC Watcher 数据恢复脚本

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

# 配置
BACKUP_DIR="$PROJECT_DIR/backups"

# 显示使用方法
show_usage() {
    echo "用法: $0 [backup_name]"
    echo
    echo "参数:"
    echo "  backup_name    备份名称或压缩文件名（可选）"
    echo
    echo "如果未提供备份名称，脚本将列出可用的备份供选择"
    echo
    echo "示例:"
    echo "  $0 btc_watcher_backup_20240101_120000"
    echo "  $0 btc_watcher_backup_20240101_120000.tar.gz"
}

# 列出可用备份
list_backups() {
    log_info "可用的备份:"

    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "备份目录不存在: $BACKUP_DIR"
        return 1
    fi

    local backups=()
    local index=1

    # 列出压缩备份
    for backup in "$BACKUP_DIR"/*.tar.gz; do
        if [ -f "$backup" ]; then
            local basename=$(basename "$backup")
            backups+=("$basename")
            echo "  $index. $basename (压缩文件)"
            ((index++))
        fi
    done

    # 列出目录备份
    for backup in "$BACKUP_DIR"/btc_watcher_backup_*; do
        if [ -d "$backup" ]; then
            local basename=$(basename "$backup")
            backups+=("$basename")
            echo "  $index. $basename (目录)"
            ((index++))
        fi
    done

    if [ ${#backups[@]} -eq 0 ]; then
        log_error "没有找到可用的备份"
        return 1
    fi

    echo
    read -p "请选择要恢复的备份 (1-${#backups[@]}): " -r selection

    if [[ ! "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#backups[@]} ]; then
        log_error "无效的选择"
        return 1
    fi

    SELECTED_BACKUP="${backups[$((selection-1))]}"
    log_info "已选择备份: $SELECTED_BACKUP"
}

# 解压备份文件
extract_backup() {
    local backup_name="$1"
    local backup_path="$BACKUP_DIR/$backup_name"

    if [[ "$backup_name" == *.tar.gz ]]; then
        log_info "解压备份文件..."

        local extract_dir="${backup_name%.tar.gz}"

        if [ -d "$BACKUP_DIR/$extract_dir" ]; then
            log_warning "解压目录已存在，是否覆盖? (y/N)"
            read -n 1 -r overwrite
            echo

            if [[ ! $overwrite =~ ^[Yy]$ ]]; then
                log_info "取消恢复操作"
                return 1
            fi

            rm -rf "$BACKUP_DIR/$extract_dir"
        fi

        cd "$BACKUP_DIR"
        tar -xzf "$backup_name"

        if [ $? -eq 0 ]; then
            log_success "备份文件解压完成"
            BACKUP_PATH="$BACKUP_DIR/$extract_dir"
        else
            log_error "备份文件解压失败"
            return 1
        fi
    else
        BACKUP_PATH="$backup_path"
    fi

    if [ ! -d "$BACKUP_PATH" ]; then
        log_error "备份目录不存在: $BACKUP_PATH"
        return 1
    fi
}

# 检查备份完整性
verify_backup() {
    log_info "验证备份完整性..."

    local required_files=(
        "backup_info.txt"
        "database.sql"
        "configs/.env"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$BACKUP_PATH/$file" ]; then
            log_error "备份文件不完整，缺少: $file"
            return 1
        fi
    done

    log_success "备份完整性验证通过"
}

# 停止现有服务
stop_current_services() {
    log_info "停止当前服务..."

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        if docker-compose ps -q | grep -q .; then
            docker-compose down
            log_success "当前服务已停止"
        else
            log_info "没有运行中的服务"
        fi
    else
        if docker compose ps -q 2>/dev/null | grep -q .; then
            docker compose down
            log_success "当前服务已停止"
        else
            log_info "没有运行中的服务"
        fi
    fi
}

# 备份当前数据
backup_current_data() {
    log_info "备份当前数据..."

    local current_backup_dir="$PROJECT_DIR/data_backup_$(date +%Y%m%d_%H%M%S)"

    if [ -d "$PROJECT_DIR/data" ]; then
        cp -r "$PROJECT_DIR/data" "$current_backup_dir"
        log_success "当前数据已备份到: $current_backup_dir"
        log_info "如果恢复失败，可以手动恢复此备份"
    else
        log_info "没有现有数据需要备份"
    fi
}

# 恢复配置文件
restore_configs() {
    log_info "恢复配置文件..."

    # 恢复环境配置
    if [ -f "$BACKUP_PATH/configs/.env" ]; then
        cp "$BACKUP_PATH/configs/.env" "$PROJECT_DIR/"
        log_success "环境配置已恢复"
    fi

    # 恢复FreqTrade配置
    if [ -d "$BACKUP_PATH/configs/user_data" ]; then
        rm -rf "$PROJECT_DIR/freqtrade/user_data"
        cp -r "$BACKUP_PATH/configs/user_data" "$PROJECT_DIR/freqtrade/"
        log_success "FreqTrade配置已恢复"
    fi

    # 恢复其他配置文件
    local configs=(
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "nginx/nginx.conf"
    )

    for config in "${configs[@]}"; do
        if [ -f "$BACKUP_PATH/configs/$config" ]; then
            local config_dir=$(dirname "$PROJECT_DIR/$config")
            mkdir -p "$config_dir"
            cp "$BACKUP_PATH/configs/$config" "$PROJECT_DIR/$config"
            log_info "已恢复: $config"
        fi
    done

    log_success "配置文件恢复完成"
}

# 恢复数据文件
restore_data_files() {
    log_info "恢复数据文件..."

    # 创建数据目录
    mkdir -p "$PROJECT_DIR/data"

    # 恢复Redis数据
    if [ -d "$BACKUP_PATH/redis" ]; then
        rm -rf "$PROJECT_DIR/data/redis"
        cp -r "$BACKUP_PATH/redis" "$PROJECT_DIR/data/"
        log_success "Redis数据已恢复"
    fi

    # 恢复其他数据文件
    if [ -d "$BACKUP_PATH/data" ]; then
        cp -r "$BACKUP_PATH/data"/* "$PROJECT_DIR/data/" 2>/dev/null || true
        log_success "数据文件已恢复"
    fi
}

# 启动数据库服务
start_database() {
    log_info "启动数据库服务..."

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        docker-compose up -d db
    else
        docker compose up -d db
    fi

    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 15
}

# 恢复数据库
restore_database() {
    log_info "恢复数据库..."

    # 检查数据库备份文件
    if [ ! -f "$BACKUP_PATH/database.sql" ]; then
        log_error "数据库备份文件不存在"
        return 1
    fi

    # 获取数据库配置
    source "$PROJECT_DIR/.env" || {
        log_error "无法读取 .env 文件"
        return 1
    }

    # 删除现有数据库并重建
    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        docker-compose exec -T db dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
        docker-compose exec -T db createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
        docker-compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_PATH/database.sql"
    else
        docker compose exec -T db dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
        docker compose exec -T db createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
        docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_PATH/database.sql"
    fi

    if [ $? -eq 0 ]; then
        log_success "数据库恢复完成"
    else
        log_error "数据库恢复失败"
        return 1
    fi
}

# 启动所有服务
start_all_services() {
    log_info "启动所有服务..."

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10

    # 检查服务状态
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    log_success "服务启动完成"
}

# 验证恢复结果
verify_restore() {
    log_info "验证恢复结果..."

    # 检查API服务
    local api_ready=false
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ] && [ "$api_ready" = false ]; do
        if curl -s http://localhost/api/v1/health &>/dev/null; then
            api_ready=true
        else
            log_info "等待API服务启动... ($attempt/$max_attempts)"
            sleep 3
            ((attempt++))
        fi
    done

    if [ "$api_ready" = true ]; then
        log_success "服务恢复验证通过"
    else
        log_warning "API服务可能存在问题，请检查日志"
    fi
}

# 主函数
main() {
    echo "================================"
    echo "    BTC Watcher 恢复脚本"
    echo "================================"
    echo

    # 解析参数
    local backup_name="$1"

    if [ -z "$backup_name" ]; then
        list_backups || exit 1
        backup_name="$SELECTED_BACKUP"
    fi

    log_info "开始恢复 BTC Watcher 数据..."
    log_info "备份名称: $backup_name"

    # 确认恢复操作
    echo
    log_warning "警告: 恢复操作将覆盖所有当前数据!"
    read -p "确认执行恢复操作? (y/N): " -n 1 -r confirm
    echo

    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_info "取消恢复操作"
        exit 0
    fi

    # 执行恢复步骤
    extract_backup "$backup_name" && \
    verify_backup && \
    stop_current_services && \
    backup_current_data && \
    restore_configs && \
    restore_data_files && \
    start_database && \
    restore_database && \
    start_all_services && \
    verify_restore

    if [ $? -eq 0 ]; then
        echo
        log_success "恢复完成!"
        log_info "BTC Watcher 已从备份恢复并启动"
        log_info "访问地址: http://localhost"
    else
        log_error "恢复过程中出现错误"
        log_info "请检查日志或手动恢复"
        exit 1
    fi
}

# 检查参数
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

# 如果脚本被直接执行（而不是被source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi