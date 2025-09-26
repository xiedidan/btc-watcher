#!/bin/bash

# BTC Watcher 数据备份脚本

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
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="btc_watcher_backup_$TIMESTAMP"

# 创建备份目录
create_backup_dir() {
    log_info "创建备份目录..."
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    log_success "备份目录已创建: $BACKUP_DIR/$BACKUP_NAME"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."

    cd "$PROJECT_DIR"

    # 检查数据库容器是否运行
    if command -v docker-compose &> /dev/null; then
        local db_container=$(docker-compose ps -q db)
    else
        local db_container=$(docker compose ps -q db)
    fi

    if [ -z "$db_container" ]; then
        log_error "数据库容器未运行，无法备份"
        return 1
    fi

    # 获取数据库配置
    source "$PROJECT_DIR/.env" 2>/dev/null || {
        log_error "无法读取 .env 文件"
        return 1
    }

    # 执行数据库备份
    local backup_file="$BACKUP_DIR/$BACKUP_NAME/database.sql"

    if command -v docker-compose &> /dev/null; then
        docker-compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$backup_file"
    else
        docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$backup_file"
    fi

    if [ $? -eq 0 ]; then
        log_success "数据库备份完成: $backup_file"
    else
        log_error "数据库备份失败"
        return 1
    fi
}

# 备份Redis数据
backup_redis() {
    log_info "备份Redis数据..."

    local redis_data_dir="$PROJECT_DIR/data/redis"
    local backup_redis_dir="$BACKUP_DIR/$BACKUP_NAME/redis"

    if [ -d "$redis_data_dir" ]; then
        cp -r "$redis_data_dir" "$backup_redis_dir"
        log_success "Redis数据备份完成: $backup_redis_dir"
    else
        log_warning "Redis数据目录不存在，跳过Redis备份"
    fi
}

# 备份配置文件
backup_configs() {
    log_info "备份配置文件..."

    local config_backup_dir="$BACKUP_DIR/$BACKUP_NAME/configs"
    mkdir -p "$config_backup_dir"

    # 备份环境配置
    if [ -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env" "$config_backup_dir/"
        log_success "环境配置已备份"
    fi

    # 备份FreqTrade策略
    if [ -d "$PROJECT_DIR/freqtrade/user_data" ]; then
        cp -r "$PROJECT_DIR/freqtrade/user_data" "$config_backup_dir/"
        log_success "FreqTrade策略已备份"
    fi

    # 备份其他配置
    local configs=(
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "nginx/nginx.conf"
    )

    for config in "${configs[@]}"; do
        if [ -f "$PROJECT_DIR/$config" ]; then
            local config_dir=$(dirname "$config")
            mkdir -p "$config_backup_dir/$config_dir"
            cp "$PROJECT_DIR/$config" "$config_backup_dir/$config"
        fi
    done

    log_success "配置文件备份完成"
}

# 备份信号和策略数据
backup_data_files() {
    log_info "备份数据文件..."

    local data_backup_dir="$BACKUP_DIR/$BACKUP_NAME/data"
    mkdir -p "$data_backup_dir"

    # 备份信号文件
    if [ -d "$PROJECT_DIR/data/signals" ]; then
        cp -r "$PROJECT_DIR/data/signals" "$data_backup_dir/"
        log_success "信号数据已备份"
    fi

    # 备份策略文件
    if [ -d "$PROJECT_DIR/data/strategies" ]; then
        cp -r "$PROJECT_DIR/data/strategies" "$data_backup_dir/"
        log_success "策略数据已备份"
    fi

    # 备份日志文件 (可选，通常很大)
    read -p "是否备份日志文件? 这可能占用大量空间 (y/N): " -n 1 -r backup_logs
    echo

    if [[ $backup_logs =~ ^[Yy]$ ]]; then
        if [ -d "$PROJECT_DIR/data/logs" ]; then
            cp -r "$PROJECT_DIR/data/logs" "$data_backup_dir/"
            log_success "日志文件已备份"
        fi
    else
        log_info "跳过日志文件备份"
    fi
}

# 创建备份信息文件
create_backup_info() {
    log_info "创建备份信息文件..."

    local info_file="$BACKUP_DIR/$BACKUP_NAME/backup_info.txt"

    cat > "$info_file" << EOF
BTC Watcher 备份信息
==================

备份时间: $(date)
备份名称: $BACKUP_NAME
备份路径: $BACKUP_DIR/$BACKUP_NAME

包含内容:
- 数据库备份 (PostgreSQL)
- Redis数据
- 配置文件
- 信号和策略数据
$([ "$backup_logs" = "y" ] && echo "- 日志文件")

系统信息:
- 主机名: $(hostname)
- 操作系统: $(uname -a)
- Docker版本: $(docker --version)
- Docker Compose版本: $(docker-compose --version 2>/dev/null || docker compose version)

恢复说明:
使用 ./scripts/restore.sh 脚本可以恢复此备份
EOF

    log_success "备份信息文件已创建: $info_file"
}

# 压缩备份文件
compress_backup() {
    read -p "是否压缩备份文件? (Y/n): " -n 1 -r compress
    echo

    if [[ ! $compress =~ ^[Nn]$ ]]; then
        log_info "压缩备份文件..."

        cd "$BACKUP_DIR"
        tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"

        if [ $? -eq 0 ]; then
            log_success "备份已压缩: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

            # 询问是否删除原始备份目录
            read -p "是否删除未压缩的备份目录? (y/N): " -n 1 -r delete_original
            echo

            if [[ $delete_original =~ ^[Yy]$ ]]; then
                rm -rf "$BACKUP_NAME"
                log_info "原始备份目录已删除"
            fi
        else
            log_error "备份压缩失败"
        fi
    fi
}

# 清理旧备份
cleanup_old_backups() {
    read -p "是否清理7天前的旧备份? (y/N): " -n 1 -r cleanup
    echo

    if [[ $cleanup =~ ^[Yy]$ ]]; then
        log_info "清理旧备份..."

        # 删除7天前的备份文件
        find "$BACKUP_DIR" -name "btc_watcher_backup_*" -type f -mtime +7 -delete 2>/dev/null || true
        find "$BACKUP_DIR" -name "btc_watcher_backup_*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

        log_success "旧备份清理完成"
    fi
}

# 主函数
main() {
    echo "================================"
    echo "    BTC Watcher 备份脚本"
    echo "================================"
    echo

    log_info "开始备份 BTC Watcher 数据..."

    # 检查Docker环境
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或未在PATH中"
        exit 1
    fi

    create_backup_dir

    # 执行各项备份任务
    backup_database && \
    backup_redis && \
    backup_configs && \
    backup_data_files && \
    create_backup_info

    if [ $? -eq 0 ]; then
        compress_backup
        cleanup_old_backups

        echo
        log_success "备份完成!"
        log_info "备份位置: $BACKUP_DIR/$BACKUP_NAME"
        echo
        log_info "恢复命令: ./scripts/restore.sh $BACKUP_NAME"
    else
        log_error "备份过程中出现错误"
        exit 1
    fi
}

# 如果脚本被直接执行（而不是被source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi