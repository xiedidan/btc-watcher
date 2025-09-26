#!/bin/bash

# BTC Watcher 日志查看脚本

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

# 显示使用方法
show_usage() {
    echo "BTC Watcher 日志查看工具"
    echo
    echo "用法: $0 [服务名称] [选项]"
    echo
    echo "服务名称:"
    echo "  all          - 所有服务日志"
    echo "  api          - 后端API服务"
    echo "  web          - 前端Web服务"
    echo "  freqtrade    - FreqTrade策略服务"
    echo "  notification - 通知服务"
    echo "  db           - 数据库服务"
    echo "  redis        - Redis缓存服务"
    echo "  nginx        - Nginx代理服务"
    echo
    echo "选项:"
    echo "  -f, --follow     跟踪日志输出 (实时显示新日志)"
    echo "  -t, --tail N     显示最后N行 (默认100行)"
    echo "  -s, --since TIME 显示指定时间后的日志 (如: 1h, 30m, 2021-01-01)"
    echo "  -h, --help       显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 api -f                 # 实时查看API服务日志"
    echo "  $0 all --tail 50          # 查看所有服务最后50行日志"
    echo "  $0 freqtrade --since 1h   # 查看FreqTrade最近1小时日志"
}

# 检查服务是否运行
check_services() {
    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        local running_services=$(docker-compose ps --services --filter "status=running")
    else
        local running_services=$(docker compose ps --services --filter "status=running")
    fi

    if [ -z "$running_services" ]; then
        echo -e "${RED}错误: 没有运行中的服务${NC}"
        echo "请先使用 ./scripts/start.sh 启动服务"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_info "当前服务状态:"
    echo

    cd "$PROJECT_DIR"

    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    echo
}

# 查看日志
view_logs() {
    local service="$1"
    local follow="$2"
    local tail="$3"
    local since="$4"

    cd "$PROJECT_DIR"

    local docker_cmd=""
    if command -v docker-compose &> /dev/null; then
        docker_cmd="docker-compose"
    else
        docker_cmd="docker compose"
    fi

    # 构建日志命令
    local log_cmd="$docker_cmd logs"

    # 添加选项
    if [ "$follow" = "true" ]; then
        log_cmd="$log_cmd -f"
    fi

    if [ -n "$tail" ]; then
        log_cmd="$log_cmd --tail $tail"
    fi

    if [ -n "$since" ]; then
        log_cmd="$log_cmd --since $since"
    fi

    # 添加服务名称
    if [ "$service" != "all" ]; then
        log_cmd="$log_cmd $service"
    fi

    log_info "执行命令: $log_cmd"
    echo

    # 执行日志命令
    eval "$log_cmd"
}

# 主函数
main() {
    local service="all"
    local follow="false"
    local tail="100"
    local since=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--follow)
                follow="true"
                shift
                ;;
            -t|--tail)
                tail="$2"
                shift 2
                ;;
            -s|--since)
                since="$2"
                shift 2
                ;;
            api|web|freqtrade|notification|db|redis|nginx|all)
                service="$1"
                shift
                ;;
            *)
                echo -e "${RED}错误: 未知参数 $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done

    echo "================================"
    echo "    BTC Watcher 日志查看"
    echo "================================"
    echo

    # 检查Docker环境
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装或未在PATH中${NC}"
        exit 1
    fi

    check_services
    show_status

    log_info "查看服务: $service"
    if [ "$follow" = "true" ]; then
        log_info "模式: 实时跟踪"
        echo -e "${YELLOW}提示: 按 Ctrl+C 退出日志跟踪${NC}"
    else
        log_info "显示行数: $tail"
    fi

    if [ -n "$since" ]; then
        log_info "时间范围: $since 至今"
    fi

    echo

    view_logs "$service" "$follow" "$tail" "$since"
}

# 如果脚本被直接执行（而不是被source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi