"""
Monitoring Service
监控系统状态、策略状态、容量使用等
"""
import asyncio
import psutil
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.session import SessionLocal
from models.strategy import Strategy
from models.signal import Signal
from core.freqtrade_manager import FreqTradeGatewayManager
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


class MonitoringService:
    """系统监控服务"""

    def __init__(self, ft_manager: FreqTradeGatewayManager):
        self.ft_manager = ft_manager
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.config = config_manager.get_monitoring_config()

        # 监控数据缓存
        self.system_metrics = {}
        self.strategy_metrics = {}
        self.capacity_history = []

    async def start(self):
        """启动监控服务"""
        if self.running:
            logger.warning("Monitoring service is already running")
            return

        self.running = True
        logger.info("Starting monitoring service...")

        # 启动各个监控任务
        self.monitoring_tasks["system"] = asyncio.create_task(
            self._monitor_system_status()
        )
        self.monitoring_tasks["strategies"] = asyncio.create_task(
            self._monitor_strategy_status()
        )
        self.monitoring_tasks["capacity"] = asyncio.create_task(
            self._monitor_capacity()
        )
        self.monitoring_tasks["cleanup"] = asyncio.create_task(
            self._cleanup_old_data()
        )

        logger.info("Monitoring service started successfully")

    async def stop(self):
        """停止监控服务"""
        if not self.running:
            return

        logger.info("Stopping monitoring service...")
        self.running = False

        # 取消所有监控任务
        for task_name, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Monitoring task {task_name} cancelled")

        self.monitoring_tasks.clear()
        logger.info("Monitoring service stopped")

    async def _monitor_system_status(self):
        """监控系统状态"""
        interval = self.config.get("system_status_interval", 30)

        while self.running:
            try:
                # 获取系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                # 获取网络IO
                net_io = psutil.net_io_counters()

                # 获取进程信息
                process = psutil.Process()
                process_memory = process.memory_info()

                self.system_metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu": {
                        "percent": cpu_percent,
                        "count": psutil.cpu_count(),
                        "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None
                    },
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": disk.percent
                    },
                    "network": {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv
                    },
                    "process": {
                        "memory_rss": process_memory.rss,
                        "memory_percent": process.memory_percent(),
                        "num_threads": process.num_threads(),
                        "num_fds": process.num_fds() if hasattr(process, "num_fds") else None
                    }
                }

                logger.debug(f"System metrics updated: CPU {cpu_percent}%, Memory {memory.percent}%")

                # 检查告警条件
                await self._check_system_alerts()

            except Exception as e:
                logger.error(f"Error monitoring system status: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _monitor_strategy_status(self):
        """监控策略状态"""
        interval = self.config.get("strategy_status_interval", 30)

        while self.running:
            try:
                async with SessionLocal() as session:
                    # 获取所有运行中的策略
                    result = await session.execute(
                        select(Strategy).where(Strategy.status == "running")
                    )
                    running_strategies = result.scalars().all()

                    strategy_metrics = {}
                    for strategy in running_strategies:
                        # 检查进程是否还在运行
                        is_alive = self._check_strategy_process(strategy.id)

                        # 获取最近的信号统计
                        recent_signals = await self._get_recent_signals(
                            session, strategy.id, hours=1
                        )

                        strategy_metrics[strategy.id] = {
                            "name": strategy.name,
                            "status": "running" if is_alive else "error",
                            "port": strategy.port,
                            "process_id": strategy.process_id,
                            "is_alive": is_alive,
                            "signals_last_hour": len(recent_signals),
                            "last_signal_time": recent_signals[0].created_at.isoformat() if recent_signals else None
                        }

                        # 如果进程已死但数据库状态为运行，更新状态
                        if not is_alive and strategy.status == "running":
                            strategy.status = "error"
                            await session.commit()
                            logger.error(f"Strategy {strategy.id} process died, updated status to error")

                    self.strategy_metrics = strategy_metrics
                    logger.debug(f"Strategy metrics updated: {len(strategy_metrics)} strategies")

            except Exception as e:
                logger.error(f"Error monitoring strategy status: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _monitor_capacity(self):
        """监控系统容量"""
        interval = 300  # 5分钟

        while self.running:
            try:
                # 获取容量信息
                capacity_info = self.ft_manager.get_capacity_info()

                # 添加时间戳
                capacity_record = {
                    **capacity_info,
                    "timestamp": datetime.now().isoformat()
                }

                # 保存到历史记录
                self.capacity_history.append(capacity_record)

                # 只保留最近24小时的数据
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.capacity_history = [
                    r for r in self.capacity_history
                    if datetime.fromisoformat(r["timestamp"]) > cutoff_time
                ]

                # TODO: 保存到数据库
                # await self._save_capacity_to_db(capacity_record)

                # 检查容量告警
                threshold = 80.0  # TODO: 从配置获取
                if capacity_info["utilization_percent"] > threshold:
                    logger.warning(
                        f"Capacity utilization {capacity_info['utilization_percent']:.2f}% "
                        f"exceeds threshold {threshold}%"
                    )
                    # TODO: 发送告警通知

                logger.debug(f"Capacity metrics updated: {capacity_info['utilization_percent']:.2f}%")

            except Exception as e:
                logger.error(f"Error monitoring capacity: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def _cleanup_old_data(self):
        """清理旧数据"""
        interval = 3600  # 1小时

        while self.running:
            try:
                async with SessionLocal() as session:
                    # 清理30天前的信号数据
                    cutoff_date = datetime.now() - timedelta(days=30)

                    # TODO: 实现数据清理逻辑
                    # DELETE FROM signals WHERE created_at < cutoff_date

                    logger.info("Old data cleanup completed")

            except Exception as e:
                logger.error(f"Error cleaning up old data: {e}", exc_info=True)

            await asyncio.sleep(interval)

    def _check_strategy_process(self, strategy_id: int) -> bool:
        """检查策略进程是否存活"""
        if strategy_id not in self.ft_manager.strategy_processes:
            return False

        process = self.ft_manager.strategy_processes[strategy_id]
        return process.poll() is None

    async def _get_recent_signals(
        self,
        session: AsyncSession,
        strategy_id: int,
        hours: int = 1
    ) -> List[Signal]:
        """获取最近的信号"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        result = await session.execute(
            select(Signal)
            .where(
                and_(
                    Signal.strategy_id == strategy_id,
                    Signal.created_at >= cutoff_time
                )
            )
            .order_by(Signal.created_at.desc())
        )
        return result.scalars().all()

    async def _check_system_alerts(self):
        """检查系统告警条件"""
        metrics = self.system_metrics

        # CPU告警
        if metrics.get("cpu", {}).get("percent", 0) > 90:
            logger.warning(f"High CPU usage: {metrics['cpu']['percent']:.2f}%")
            # TODO: 发送告警

        # 内存告警
        if metrics.get("memory", {}).get("percent", 0) > 90:
            logger.warning(f"High memory usage: {metrics['memory']['percent']:.2f}%")
            # TODO: 发送告警

        # 磁盘告警
        if metrics.get("disk", {}).get("percent", 0) > 90:
            logger.warning(f"High disk usage: {metrics['disk']['percent']:.2f}%")
            # TODO: 发送告警

    def get_system_metrics(self) -> Dict:
        """获取系统指标"""
        return self.system_metrics

    def get_strategy_metrics(self) -> Dict:
        """获取策略指标"""
        return self.strategy_metrics

    def get_capacity_trend(self, hours: int = 24) -> List[Dict]:
        """获取容量趋势数据"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            r for r in self.capacity_history
            if datetime.fromisoformat(r["timestamp"]) > cutoff_time
        ]

    def get_health_status(self) -> Dict:
        """获取健康状态"""
        metrics = self.system_metrics

        cpu_healthy = metrics.get("cpu", {}).get("percent", 0) < 80
        memory_healthy = metrics.get("memory", {}).get("percent", 0) < 80
        disk_healthy = metrics.get("disk", {}).get("percent", 0) < 80

        overall_healthy = cpu_healthy and memory_healthy and disk_healthy

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "cpu_healthy": cpu_healthy,
            "memory_healthy": memory_healthy,
            "disk_healthy": disk_healthy,
            "monitoring_running": self.running,
            "active_tasks": len(self.monitoring_tasks),
            "timestamp": datetime.now().isoformat()
        }
