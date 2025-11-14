"""
策略日志监控服务
监控FreqTrade策略日志文件，实时推送新日志到WebSocket客户端
"""
import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Set
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from services.websocket_service import ws_service

logger = logging.getLogger(__name__)


class LogFileHandler(FileSystemEventHandler):
    """日志文件变化处理器"""

    def __init__(self, log_monitor: 'LogMonitorService'):
        self.log_monitor = log_monitor
        super().__init__()

    def on_modified(self, event):
        """文件修改事件处理"""
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.log'):
            # 从文件路径提取strategy_id
            filename = Path(event.src_path).name
            match = re.match(r'strategy_(\d+)\.log', filename)
            if match:
                strategy_id = int(match.group(1))
                logger.info(f"File modified event detected for strategy {strategy_id}: {event.src_path}")
                # 触发日志读取和推送（线程安全）
                if self.log_monitor.event_loop:
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.log_monitor.process_new_logs(strategy_id, event.src_path),
                            self.log_monitor.event_loop
                        )
                        logger.info(f"Coroutine scheduled for strategy {strategy_id}")
                    except Exception as e:
                        logger.error(f"Failed to schedule coroutine for strategy {strategy_id}: {e}", exc_info=True)
                else:
                    logger.warning(f"Event loop not available, cannot process logs for strategy {strategy_id}")


class LogMonitorService:
    """日志监控服务"""

    def __init__(self, logs_path: Path):
        self.logs_path = logs_path
        self.observer = Observer()
        self.file_positions: Dict[int, int] = {}  # strategy_id -> file_position
        self.monitored_strategies: Set[int] = set()  # 正在监控的策略ID
        self.running = False
        self.event_loop = None  # 保存主事件循环引用

        # 日志解析正则表达式
        # 格式: 2025-10-27 16:55:41,203 - freqtrade.freqtradebot - INFO - Message
        self.log_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([\w\.]+) - (\w+) - (.+)'
        )

    def start(self):
        """启动日志监控"""
        if not self.running:
            # 保存当前事件循环的引用
            try:
                self.event_loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("No running event loop found, log monitoring may not work properly")

            handler = LogFileHandler(self)
            self.observer.schedule(handler, str(self.logs_path), recursive=False)
            self.observer.start()
            self.running = True
            logger.info(f"Log monitor service started, watching: {self.logs_path}")

    def stop(self):
        """停止日志监控"""
        if self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False
            logger.info("Log monitor service stopped")

    async def start_monitoring_strategy(self, strategy_id: int):
        """开始监控指定策略的日志"""
        if strategy_id in self.monitored_strategies:
            logger.debug(f"Strategy {strategy_id} is already being monitored")
            return

        log_file = self.logs_path / f"strategy_{strategy_id}.log"

        if log_file.exists():
            # 记录当前文件位置（从文件末尾开始）
            self.file_positions[strategy_id] = log_file.stat().st_size
            self.monitored_strategies.add(strategy_id)
            logger.info(f"Started monitoring strategy {strategy_id} logs at position {self.file_positions[strategy_id]}")
        else:
            # 文件不存在，设置位置为0（等待文件创建）
            self.file_positions[strategy_id] = 0
            self.monitored_strategies.add(strategy_id)
            logger.info(f"Waiting for strategy {strategy_id} log file to be created")

    async def stop_monitoring_strategy(self, strategy_id: int):
        """停止监控指定策略的日志"""
        if strategy_id in self.monitored_strategies:
            self.monitored_strategies.remove(strategy_id)
            if strategy_id in self.file_positions:
                del self.file_positions[strategy_id]
            logger.info(f"Stopped monitoring strategy {strategy_id} logs")

    async def process_new_logs(self, strategy_id: int, log_file_path: str):
        """处理新增的日志内容"""
        logger.info(f"[process_new_logs] START - Processing new logs for strategy {strategy_id}")

        # 移除monitored_strategies检查，因为uvicorn重载会清空这个集合
        # 如果文件修改事件被触发，说明之前肯定在监控中，应该继续处理

        try:
            log_file = Path(log_file_path)

            if not log_file.exists():
                return

            current_size = log_file.stat().st_size
            last_position = self.file_positions.get(strategy_id, 0)

            logger.info(f"[process_new_logs] Strategy {strategy_id}: current_size={current_size}, last_position={last_position}")

            # 如果文件缩小了（可能是日志轮转），从头开始读
            if current_size < last_position:
                last_position = 0
                logger.info(f"[process_new_logs] File size decreased, resetting position to 0")

            # 如果没有新内容，直接返回
            if current_size == last_position:
                logger.info(f"[process_new_logs] No new content for strategy {strategy_id}, skipping")
                return

            # 读取新增内容
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                self.file_positions[strategy_id] = f.tell()
                logger.info(f"[process_new_logs] Read {len(new_lines)} new lines for strategy {strategy_id}")

            # 解析并推送每一行日志
            pushed_count = 0
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue

                log_entry = self._parse_log_line(line)
                if log_entry:
                    # 推送到WebSocket
                    await ws_service.push_strategy_log(strategy_id, log_entry)
                    pushed_count += 1

            logger.info(f"[process_new_logs] Pushed {pushed_count} log entries for strategy {strategy_id}")

        except Exception as e:
            logger.error(f"Error processing logs for strategy {strategy_id}: {e}", exc_info=True)

    def _parse_log_line(self, line: str) -> Optional[Dict]:
        """解析日志行"""
        match = self.log_pattern.match(line)

        if match:
            timestamp_str, logger_name, level, message = match.groups()

            return {
                "timestamp": timestamp_str,
                "logger": logger_name,
                "level": level,
                "message": message,
                "raw": line
            }
        else:
            # 如果无法解析，返回原始内容
            return {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "logger": "unknown",
                "level": "INFO",
                "message": line,
                "raw": line
            }

    async def get_recent_logs(self, strategy_id: int, lines: int = 100) -> list:
        """获取策略的最近N行日志"""
        log_file = self.logs_path / f"strategy_{strategy_id}.log"

        if not log_file.exists():
            return []

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # 解析日志行
            parsed_logs = []
            for line in recent_lines:
                line = line.strip()
                if line:
                    log_entry = self._parse_log_line(line)
                    if log_entry:
                        parsed_logs.append(log_entry)

            return parsed_logs

        except Exception as e:
            logger.error(f"Error reading recent logs for strategy {strategy_id}: {e}", exc_info=True)
            return []


# 全局实例（将在main.py中初始化）
log_monitor_service: Optional[LogMonitorService] = None
