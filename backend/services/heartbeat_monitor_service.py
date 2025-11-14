"""
Strategy Heartbeat Monitoring Service

This service monitors FreqTrade strategy process heartbeats by reading log files
and automatically restarts strategies that have timed out (if configured to do so).
"""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
from pathlib import Path
import logging

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.heartbeat import StrategyHeartbeatConfig, StrategyHeartbeatHistory, StrategyRestartHistory
from models.strategy import Strategy
from database.session import SessionLocal

logger = logging.getLogger(__name__)


class HeartbeatStatus:
    """心跳状态数据类"""

    def __init__(self, strategy_id: int, log_file_path: str, timeout: int, auto_restart: bool):
        self.strategy_id = strategy_id
        self.log_file_path = log_file_path
        self.timeout = timeout
        self.auto_restart = auto_restart

        # 心跳状态
        self.last_heartbeat_time: Optional[datetime] = None
        self.last_pid: Optional[int] = None
        self.last_version: Optional[str] = None
        self.last_state: Optional[str] = None

        # 异常状态
        self.is_abnormal = False
        self.consecutive_failures = 0

        # 重启记录
        self.restart_count = 0
        self.last_restart_time: Optional[datetime] = None


class StrategyHeartbeatMonitor:
    """策略心跳监控服务"""

    # 心跳日志正则表达式
    # 格式: 2025-11-04 21:19:01,013 - freqtrade.worker - INFO - Bot heartbeat. PID=872423, version='2025.9.1', state='RUNNING'
    HEARTBEAT_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - freqtrade\.worker - INFO - '
        r'Bot heartbeat\. PID=(\d+), version=\'([^\']+)\', state=\'(\w+)\''
    )

    def __init__(
        self,
        strategy_manager,
        notify_hub,
        check_interval: int = 30,  # 检查间隔（秒）
    ):
        """
        初始化心跳监控服务

        Args:
            strategy_manager: 策略管理器实例
            notify_hub: 通知中心实例
            check_interval: 心跳检查间隔（秒）
        """
        self.strategy_manager = strategy_manager
        self.notify_hub = notify_hub
        self.check_interval = check_interval

        # 存储每个策略的心跳状态
        self.heartbeat_status: Dict[int, HeartbeatStatus] = {}

        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """启动心跳监控服务"""
        if self.running:
            logger.warning("Heartbeat monitor already running")
            return

        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Heartbeat monitor started")

    async def stop(self):
        """停止心跳监控服务"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat monitor stopped")

    async def register_strategy(
        self,
        strategy_id: int,
        log_file_path: str,
        timeout: Optional[int] = None,
        auto_restart: Optional[bool] = None
    ):
        """
        注册需要监控的策略

        Args:
            strategy_id: 策略ID
            log_file_path: 策略日志文件路径
            timeout: 心跳超时时间（秒），None则使用数据库配置或默认值
            auto_restart: 是否自动重启，None则使用数据库配置或默认值
        """
        # 从数据库读取配置
        async with SessionLocal() as db:
            result = await db.execute(
                select(StrategyHeartbeatConfig).where(
                    StrategyHeartbeatConfig.strategy_id == strategy_id
                )
            )
            config = result.scalar_one_or_none()

            # 如果没有配置，创建默认配置
            if not config:
                config = StrategyHeartbeatConfig(
                    strategy_id=strategy_id,
                    enabled=True,
                    timeout_seconds=timeout or 300,
                    check_interval_seconds=self.check_interval,
                    auto_restart=auto_restart if auto_restart is not None else True,
                    max_restart_attempts=3,
                    restart_cooldown_seconds=60
                )
                db.add(config)
                await db.commit()
                await db.refresh(config)

        # 创建心跳状态对象
        self.heartbeat_status[strategy_id] = HeartbeatStatus(
            strategy_id=strategy_id,
            log_file_path=log_file_path,
            timeout=config.timeout_seconds,
            auto_restart=config.auto_restart
        )
        logger.info(
            f"Registered strategy {strategy_id} for heartbeat monitoring "
            f"(timeout={config.timeout_seconds}s, auto_restart={config.auto_restart})"
        )

    async def unregister_strategy(self, strategy_id: int):
        """取消注册策略"""
        if strategy_id in self.heartbeat_status:
            del self.heartbeat_status[strategy_id]
            logger.info(f"Unregistered strategy {strategy_id} from heartbeat monitoring")

    async def update_config(
        self,
        strategy_id: int,
        timeout: Optional[int] = None,
        auto_restart: Optional[bool] = None
    ):
        """更新策略的心跳监控配置"""
        if strategy_id in self.heartbeat_status:
            status = self.heartbeat_status[strategy_id]
            if timeout is not None:
                status.timeout = timeout
            if auto_restart is not None:
                status.auto_restart = auto_restart
            logger.info(
                f"Updated heartbeat config for strategy {strategy_id}: "
                f"timeout={status.timeout}s, auto_restart={status.auto_restart}"
            )

    async def _monitor_loop(self):
        """心跳监控主循环"""
        while self.running:
            try:
                await self._check_all_strategies()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def _check_all_strategies(self):
        """检查所有策略的心跳状态"""
        for strategy_id, status in list(self.heartbeat_status.items()):
            try:
                await self._check_strategy_heartbeat(strategy_id, status)
            except Exception as e:
                logger.error(
                    f"Error checking heartbeat for strategy {strategy_id}: {e}",
                    exc_info=True
                )

    async def _check_strategy_heartbeat(
        self,
        strategy_id: int,
        status: HeartbeatStatus
    ):
        """检查单个策略的心跳状态"""
        # 读取日志文件，查找最新的心跳记录
        latest_heartbeat = await self._read_latest_heartbeat(status.log_file_path)

        if latest_heartbeat:
            # 更新心跳时间
            prev_heartbeat_time = status.last_heartbeat_time
            status.last_heartbeat_time = latest_heartbeat['timestamp']
            status.last_pid = latest_heartbeat['pid']
            status.last_version = latest_heartbeat['version']
            status.last_state = latest_heartbeat['state']

            # 计算距离上次心跳的时间
            time_since_heartbeat = 0
            if prev_heartbeat_time:
                time_since_heartbeat = int((status.last_heartbeat_time - prev_heartbeat_time).total_seconds())

            # 记录心跳历史到数据库
            await self._save_heartbeat_history(
                strategy_id=strategy_id,
                heartbeat_time=status.last_heartbeat_time,
                pid=status.last_pid,
                version=status.last_version,
                state=status.last_state,
                is_timeout=False,
                time_since_last_heartbeat=time_since_heartbeat
            )

            # 检查心跳是否超时
            current_time_since_heartbeat = (datetime.now(timezone.utc) - status.last_heartbeat_time).total_seconds()

            if current_time_since_heartbeat > status.timeout:
                # 心跳超时
                await self._handle_heartbeat_timeout(strategy_id, status, current_time_since_heartbeat)
            else:
                # 心跳正常
                if status.is_abnormal:
                    # 从异常状态恢复
                    await self._handle_heartbeat_recovered(strategy_id, status)
                status.consecutive_failures = 0
        else:
            # 没有读取到心跳记录
            if status.last_heartbeat_time:
                time_since_heartbeat = (datetime.now(timezone.utc) - status.last_heartbeat_time).total_seconds()
                if time_since_heartbeat > status.timeout:
                    await self._handle_heartbeat_timeout(strategy_id, status, time_since_heartbeat)

    async def _read_latest_heartbeat(self, log_file_path: str) -> Optional[dict]:
        """
        读取日志文件中最新的心跳记录

        Returns:
            心跳信息字典，包含 timestamp, pid, version, state
        """
        try:
            log_path = Path(log_file_path)
            if not log_path.exists():
                logger.debug(f"Log file not found: {log_file_path}")
                return None

            # 读取日志文件最后N行（避免读取整个大文件）
            last_lines = await self._read_last_lines(log_path, lines=100)

            # 从后往前查找心跳日志
            for line in reversed(last_lines):
                match = self.HEARTBEAT_PATTERN.search(line)
                if match:
                    timestamp_str, pid, version, state = match.groups()
                    # Parse timestamp from local time and convert to UTC
                    # FreqTrade logs use local system time (e.g., CST UTC+8)
                    from datetime import timedelta
                    from time import timezone as time_timezone

                    naive_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    # Get local timezone offset in seconds (e.g., -28800 for CST/UTC+8)
                    local_offset_seconds = time_timezone
                    # Convert to UTC by subtracting the local offset
                    utc_dt = naive_dt - timedelta(seconds=local_offset_seconds)
                    aware_dt = utc_dt.replace(tzinfo=timezone.utc)

                    return {
                        'timestamp': aware_dt,
                        'pid': int(pid),
                        'version': version,
                        'state': state
                    }

            return None

        except Exception as e:
            logger.error(f"Error reading heartbeat from {log_file_path}: {e}")
            return None

    async def _read_last_lines(self, file_path: Path, lines: int = 100) -> List[str]:
        """读取文件的最后N行"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 使用简单的方法读取最后N行
                return f.readlines()[-lines:]
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

    async def _handle_heartbeat_timeout(
        self,
        strategy_id: int,
        status: HeartbeatStatus,
        time_since_heartbeat: float
    ):
        """处理心跳超时"""
        status.consecutive_failures += 1
        status.is_abnormal = True

        logger.warning(
            f"Strategy {strategy_id} heartbeat timeout: "
            f"{time_since_heartbeat:.0f}s since last heartbeat "
            f"(timeout: {status.timeout}s, failures: {status.consecutive_failures})"
        )

        # 记录超时历史
        await self._save_heartbeat_history(
            strategy_id=strategy_id,
            heartbeat_time=datetime.now(timezone.utc),
            pid=status.last_pid,
            version=status.last_version,
            state=status.last_state,
            is_timeout=True,
            time_since_last_heartbeat=int(time_since_heartbeat)
        )

        # 发送告警通知
        await self.notify_hub.notify(
            user_id=1,  # 管理员
            title=f"🚨 策略心跳超时告警",
            message=(
                f"策略 #{strategy_id} 心跳超时\n"
                f"最后心跳时间: {status.last_heartbeat_time.strftime('%Y-%m-%d %H:%M:%S') if status.last_heartbeat_time else '无'}\n"
                f"超时时长: {time_since_heartbeat:.0f}秒\n"
                f"配置超时: {status.timeout}秒\n"
                f"连续失败次数: {status.consecutive_failures}\n"
                f"自动重启: {'已启用' if status.auto_restart else '已禁用'}"
            ),
            notification_type="alert",
            priority="P2",  # 高优先级
            metadata={
                "strategy_id": strategy_id,
                "time_since_heartbeat": time_since_heartbeat,
                "timeout": status.timeout,
                "consecutive_failures": status.consecutive_failures,
                "auto_restart": status.auto_restart
            },
            strategy_id=strategy_id
        )

        # 如果启用了自动重启，尝试重启策略
        if status.auto_restart:
            await self._attempt_restart(strategy_id, status)

    async def _attempt_restart(self, strategy_id: int, status: HeartbeatStatus):
        """尝试重启策略"""
        try:
            logger.info(f"Attempting to restart strategy {strategy_id} (auto_restart enabled)")

            previous_pid = status.last_pid
            success = await self.strategy_manager.restart_strategy(strategy_id)

            if success:
                # 重置心跳状态
                status.last_restart_time = datetime.now(timezone.utc)
                status.restart_count += 1

                # 获取新的PID（需要一点时间让进程启动）
                await asyncio.sleep(2)
                latest_heartbeat = await self._read_latest_heartbeat(status.log_file_path)
                new_pid = latest_heartbeat['pid'] if latest_heartbeat else None

                # 记录重启历史
                await self._save_restart_history(
                    strategy_id=strategy_id,
                    restart_reason="heartbeat_timeout",
                    restart_time=status.last_restart_time,
                    restart_success=True,
                    error_message=None,
                    previous_pid=previous_pid,
                    new_pid=new_pid
                )

                logger.info(f"Strategy {strategy_id} restarted successfully")

                # 发送重启成功通知
                await self.notify_hub.notify(
                    user_id=1,
                    title=f"✅ 策略已自动重启",
                    message=(
                        f"策略 #{strategy_id} 因心跳超时已自动重启\n"
                        f"重启次数: {status.restart_count}\n"
                        f"重启时间: {status.last_restart_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"前进程PID: {previous_pid}\n"
                        f"新进程PID: {new_pid}"
                    ),
                    notification_type="info",
                    priority="P1",
                    metadata={
                        "strategy_id": strategy_id,
                        "restart_count": status.restart_count,
                        "previous_pid": previous_pid,
                        "new_pid": new_pid
                    },
                    strategy_id=strategy_id
                )
            else:
                logger.error(f"Failed to restart strategy {strategy_id}")

                # 记录重启失败
                await self._save_restart_history(
                    strategy_id=strategy_id,
                    restart_reason="heartbeat_timeout",
                    restart_time=datetime.now(timezone.utc),
                    restart_success=False,
                    error_message="Restart command failed",
                    previous_pid=previous_pid,
                    new_pid=None
                )

                # 发送重启失败通知
                await self.notify_hub.notify(
                    user_id=1,
                    title=f"❌ 策略重启失败",
                    message=f"策略 #{strategy_id} 自动重启失败，请手动检查",
                    notification_type="alert",
                    priority="P2",
                    metadata={"strategy_id": strategy_id},
                    strategy_id=strategy_id
                )

        except Exception as e:
            logger.error(f"Error restarting strategy {strategy_id}: {e}", exc_info=True)

            # 记录异常
            await self._save_restart_history(
                strategy_id=strategy_id,
                restart_reason="heartbeat_timeout",
                restart_time=datetime.now(timezone.utc),
                restart_success=False,
                error_message=str(e),
                previous_pid=status.last_pid,
                new_pid=None
            )

    async def _handle_heartbeat_recovered(self, strategy_id: int, status: HeartbeatStatus):
        """处理心跳恢复正常"""
        status.is_abnormal = False

        logger.info(f"Strategy {strategy_id} heartbeat recovered")

        # 发送恢复通知
        await self.notify_hub.notify(
            user_id=1,
            title=f"✅ 策略心跳恢复正常",
            message=(
                f"策略 #{strategy_id} 心跳已恢复正常\n"
                f"最后心跳: {status.last_heartbeat_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"状态: {status.last_state}\n"
                f"PID: {status.last_pid}"
            ),
            notification_type="info",
            priority="P1",
            metadata={
                "strategy_id": strategy_id,
                "last_heartbeat": status.last_heartbeat_time.isoformat(),
                "pid": status.last_pid
            },
            strategy_id=strategy_id
        )

    async def _save_heartbeat_history(
        self,
        strategy_id: int,
        heartbeat_time: datetime,
        pid: Optional[int],
        version: Optional[str],
        state: Optional[str],
        is_timeout: bool,
        time_since_last_heartbeat: int
    ):
        """保存心跳历史记录到数据库"""
        try:
            async with SessionLocal() as db:
                history = StrategyHeartbeatHistory(
                    strategy_id=strategy_id,
                    heartbeat_time=heartbeat_time,
                    pid=pid,
                    version=version,
                    state=state,
                    is_timeout=is_timeout,
                    time_since_last_heartbeat_seconds=time_since_last_heartbeat
                )
                db.add(history)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save heartbeat history: {e}")

    async def _save_restart_history(
        self,
        strategy_id: int,
        restart_reason: str,
        restart_time: datetime,
        restart_success: bool,
        error_message: Optional[str],
        previous_pid: Optional[int],
        new_pid: Optional[int]
    ):
        """保存重启历史记录到数据库"""
        try:
            async with SessionLocal() as db:
                history = StrategyRestartHistory(
                    strategy_id=strategy_id,
                    restart_reason=restart_reason,
                    restart_time=restart_time,
                    restart_success=restart_success,
                    error_message=error_message,
                    previous_pid=previous_pid,
                    new_pid=new_pid
                )
                db.add(history)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save restart history: {e}")

    def get_heartbeat_status(self, strategy_id: int) -> Optional[dict]:
        """获取策略的心跳状态"""
        if strategy_id not in self.heartbeat_status:
            return None

        status = self.heartbeat_status[strategy_id]

        time_since_last_heartbeat = None
        if status.last_heartbeat_time:
            time_since_last_heartbeat = int((datetime.now(timezone.utc) - status.last_heartbeat_time).total_seconds())

        return {
            "strategy_id": strategy_id,
            "last_heartbeat_time": status.last_heartbeat_time.isoformat() if status.last_heartbeat_time else None,
            "last_pid": status.last_pid,
            "last_version": status.last_version,
            "last_state": status.last_state,
            "timeout_seconds": status.timeout,
            "auto_restart": status.auto_restart,
            "is_abnormal": status.is_abnormal,
            "consecutive_failures": status.consecutive_failures,
            "restart_count": status.restart_count,
            "last_restart_time": status.last_restart_time.isoformat() if status.last_restart_time else None,
            "time_since_last_heartbeat_seconds": time_since_last_heartbeat
        }

    async def get_all_heartbeat_status(self) -> List[dict]:
        """获取所有策略的心跳状态"""
        return [
            self.get_heartbeat_status(strategy_id)
            for strategy_id in self.heartbeat_status.keys()
        ]


# 全局单例
heartbeat_monitor: Optional[StrategyHeartbeatMonitor] = None
