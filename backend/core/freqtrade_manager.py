"""
FreqTrade Gateway Manager - Multi-Instance Mode
Manages multiple FreqTrade strategy instances with intelligent port allocation
"""
import subprocess
import psutil
import json
import os
import aiohttp
import asyncio
from typing import Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FreqTradeGatewayManager:
    """FreqTrade网关管理器 - 反向代理模式"""

    def __init__(self):
        self.strategy_processes: Dict[int, subprocess.Popen] = {}
        self.strategy_ports: Dict[int, int] = {}  # strategy_id -> port
        self.freqtrade_version = "2025.8"
        self.gateway_port = 8080  # 统一网关端口
        self.base_port = 8081  # FreqTrade实例起始端口
        self.max_port = 9080   # FreqTrade实例最大端口 (1000个端口: 8081-9080)
        self.max_strategies = 1000  # 最大并发策略数

        # 使用项目目录而不是 /app
        project_root = Path(__file__).parent.parent
        self.base_config_path = project_root / "freqtrade_configs"
        self.strategies_path = project_root / "user_data" / "strategies"
        self.logs_path = project_root / "logs" / "freqtrade"
        self.port_pool = set(range(self.base_port, self.max_port + 1))  # 可用端口池

        # Ensure directories exist
        try:
            self.base_config_path.mkdir(parents=True, exist_ok=True)
            self.strategies_path.mkdir(parents=True, exist_ok=True)
            self.logs_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"FreqTrade directories initialized at {project_root}")
        except Exception as e:
            logger.warning(f"Failed to create FreqTrade directories: {e}")
            logger.warning("FreqTrade manager will operate with reduced functionality")

    async def create_strategy(self, strategy_config: dict, db = None) -> bool:
        """创建并启动新策略"""
        strategy_id = strategy_config["id"]

        try:
            logger.info(f"Creating strategy {strategy_id}: {strategy_config.get('name', 'Unknown')}")

            # 1. 分配端口
            port = await self._allocate_port(strategy_id)
            logger.info(f"Allocated port {port} for strategy {strategy_id}")

            # 2. 生成配置文件（传递db session用于查询代理）
            config_file = await self._generate_config_file(strategy_config, port, db)
            logger.info(f"Generated config file for strategy {strategy_id}: {config_file}")

            # 3. 启动FreqTrade进程
            process = await self._start_freqtrade_process(config_file, strategy_id)
            logger.info(f"Started FreqTrade process for strategy {strategy_id} (PID: {process.pid})")

            # 4. 等待API就绪
            await self._wait_for_api_ready(port)
            logger.info(f"FreqTrade API ready for strategy {strategy_id}")

            # 5. 保存进程和端口信息
            self.strategy_processes[strategy_id] = process
            self.strategy_ports[strategy_id] = port

            # 6. 更新API Gateway路由
            await self._update_gateway_routes()

            logger.info(f"Strategy {strategy_id} started successfully on port {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to create strategy {strategy_id}: {e}", exc_info=True)
            await self._cleanup_failed_strategy(strategy_id)
            return False

    async def stop_strategy(self, strategy_id: int) -> bool:
        """停止指定策略"""
        try:
            if strategy_id not in self.strategy_processes:
                logger.warning(f"Strategy {strategy_id} not found in running processes")
                return True

            logger.info(f"Stopping strategy {strategy_id}")
            process = self.strategy_processes[strategy_id]
            port = self.strategy_ports.get(strategy_id)

            # 1. 通过API优雅停止
            if port:
                await self._graceful_stop_via_api(port)

            # 2. 强制停止进程
            await self._force_stop_process(process)

            # 3. 清理资源
            del self.strategy_processes[strategy_id]
            if strategy_id in self.strategy_ports:
                # 释放端口回端口池
                released_port = self.strategy_ports[strategy_id]
                self.port_pool.add(released_port)
                logger.info(f"Released port {released_port} back to pool")
                del self.strategy_ports[strategy_id]

            # 4. 更新API Gateway路由
            await self._update_gateway_routes()

            logger.info(f"Strategy {strategy_id} stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}", exc_info=True)
            return False

    async def stop_all_strategies(self) -> Dict[int, bool]:
        """停止所有运行中的策略"""
        results = {}
        strategy_ids = list(self.strategy_processes.keys())

        logger.info(f"Stopping {len(strategy_ids)} strategies...")

        for strategy_id in strategy_ids:
            results[strategy_id] = await self.stop_strategy(strategy_id)

        # 验证端口池状态
        logger.info(f"Port pool status: {len(self.port_pool)}/{self.max_strategies} ports available")

        return results

    def get_port_pool_status(self) -> dict:
        """获取端口池状态"""
        return {
            "total_ports": self.max_strategies,
            "available_ports": len(self.port_pool),
            "allocated_ports": self.max_strategies - len(self.port_pool),
            "running_strategies": len(self.strategy_processes),
            "port_range": f"{self.base_port}-{self.max_port}",
            "max_concurrent": self.max_strategies
        }

    def get_capacity_info(self) -> dict:
        """获取系统容量信息"""
        running = len(self.strategy_processes)
        available = len(self.port_pool)

        return {
            "max_strategies": self.max_strategies,
            "running_strategies": running,
            "available_slots": available,
            "utilization_percent": round((running / self.max_strategies) * 100, 2),
            "port_range": f"{self.base_port}-{self.max_port}",
            "can_start_more": available > 0,
            "architecture": "multi_instance_reverse_proxy"
        }

    async def check_strategy_health(self, strategy_id: int) -> dict:
        """检查单个策略的健康状态"""
        if strategy_id not in self.strategy_processes:
            return {
                "strategy_id": strategy_id,
                "status": "not_found",
                "healthy": False,
                "message": "Strategy process not found"
            }

        process = self.strategy_processes[strategy_id]
        port = self.strategy_ports.get(strategy_id)

        # 1. 检查进程是否运行
        process_running = process.poll() is None
        if not process_running:
            return {
                "strategy_id": strategy_id,
                "status": "process_dead",
                "healthy": False,
                "message": f"Process exited with code {process.returncode}",
                "port": port
            }

        # 2. 检查API是否响应
        if port:
            api_healthy = await self._check_api_health(port)
            if not api_healthy:
                return {
                    "strategy_id": strategy_id,
                    "status": "api_unhealthy",
                    "healthy": False,
                    "message": "FreqTrade API not responding",
                    "port": port,
                    "process_id": process.pid
                }

        # 3. 获取进程资源使用情况
        try:
            proc = psutil.Process(process.pid)
            cpu_percent = proc.cpu_percent(interval=1)
            memory_mb = proc.memory_info().rss / 1024 / 1024

            return {
                "strategy_id": strategy_id,
                "status": "running",
                "healthy": True,
                "port": port,
                "process_id": process.pid,
                "cpu_percent": round(cpu_percent, 2),
                "memory_mb": round(memory_mb, 2),
                "num_threads": proc.num_threads()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {
                "strategy_id": strategy_id,
                "status": "process_inaccessible",
                "healthy": False,
                "message": "Cannot access process information",
                "port": port
            }

    async def check_all_strategies_health(self) -> dict:
        """检查所有策略的健康状态"""
        results = {}
        strategy_ids = list(self.strategy_processes.keys())

        for strategy_id in strategy_ids:
            results[strategy_id] = await self.check_strategy_health(strategy_id)

        # 统计健康状态
        healthy_count = sum(1 for r in results.values() if r.get("healthy", False))
        unhealthy_count = len(results) - healthy_count

        return {
            "total_strategies": len(results),
            "healthy_strategies": healthy_count,
            "unhealthy_strategies": unhealthy_count,
            "health_details": results
        }

    async def _check_api_health(self, port: int, timeout: int = 5) -> bool:
        """检查FreqTrade API健康状态"""
        try:
            api_url = f"http://127.0.0.1:{port}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/api/v1/ping",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    return response.status == 200
        except:
            return False

    async def _allocate_port(self, strategy_id: int) -> int:
        """为策略分配端口 - 支持1000个并发策略"""
        # 检查是否超过最大策略数
        if len(self.strategy_processes) >= self.max_strategies:
            raise Exception(f"Maximum concurrent strategies limit ({self.max_strategies}) reached")

        # 优先使用策略ID对应的端口（如果可用）
        preferred_port = self.base_port + strategy_id
        if preferred_port <= self.max_port and preferred_port in self.port_pool:
            self.port_pool.remove(preferred_port)
            return preferred_port

        # 如果首选端口不可用，从端口池中分配第一个可用端口
        if not self.port_pool:
            raise Exception("No available ports in the pool")

        allocated_port = min(self.port_pool)  # 分配最小的可用端口
        self.port_pool.remove(allocated_port)

        logger.info(f"Allocated port {allocated_port} for strategy {strategy_id}")
        return allocated_port

    async def _generate_config_file(self, strategy_config: dict, port: int, db = None) -> str:
        """生成FreqTrade配置文件"""
        # 获取代理配置
        proxy_config = await self._get_proxy_config(strategy_config.get("proxy_id"), db)

        config = {
            "strategy": strategy_config["strategy_class"],
            "strategy_path": str(self.strategies_path),
            "timeframe": strategy_config["timeframe"],
            "dry_run": strategy_config.get("dry_run", True),
            "dry_run_wallet": strategy_config.get("dry_run_wallet", 1000),

            "exchange": {
                "name": strategy_config["exchange"],
                "key": "",
                "secret": "",
                "ccxt_config": {
                    "enableRateLimit": True,
                    "proxies": proxy_config
                },
                "pair_whitelist": strategy_config["pair_whitelist"],
                "pair_blacklist": strategy_config.get("pair_blacklist", [])
            },

            "pairlists": [{"method": "StaticPairList"}],

            # 独立API端口配置
            "api_server": {
                "enabled": True,
                "listen_ip_address": "127.0.0.1",
                "listen_port": port,
                "verbosity": "info",
                "enable_openapi": True,
                "jwt_secret_key": f"btc-watcher-strategy-{strategy_config['id']}",
                "CORS_origins": ["http://localhost:8000", "http://localhost:8080"]
            },

            # 信号输出配置
            "webhook": {
                "enabled": True,
                "url": f"http://localhost:8000/api/v1/signals/webhook/{strategy_config['id']}",
                "format": "json",
                "strategy_version": strategy_config.get("version", "v1.0")
            },

            "initial_state": "running",
            "internals": {
                "process_throttle_secs": 5
            }
        }

        # 保存策略专用配置文件
        config_file = self.base_config_path / f"strategy_{strategy_config['id']}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return str(config_file)

    async def _start_freqtrade_process(self, config_file: str, strategy_id: int) -> subprocess.Popen:
        """启动FreqTrade进程"""
        log_file = self.logs_path / f"strategy_{strategy_id}.log"

        cmd = [
            "freqtrade", "trade",
            "--config", config_file,
            "--logfile", str(log_file)
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        return process

    async def _wait_for_api_ready(self, port: int, timeout: int = 60):
        """等待FreqTrade API就绪"""
        start_time = asyncio.get_event_loop().time()
        api_url = f"http://127.0.0.1:{port}"

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{api_url}/api/v1/ping",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            return True
            except:
                pass

            await asyncio.sleep(2)

        raise Exception(f"FreqTrade API on port {port} failed to start within {timeout}s")

    async def _update_gateway_routes(self):
        """更新API Gateway路由配置"""
        routes = {}
        for strategy_id, port in self.strategy_ports.items():
            routes[str(strategy_id)] = {
                "upstream": f"http://127.0.0.1:{port}",
                "health_check": f"http://127.0.0.1:{port}/api/v1/ping"
            }

        # 保存路由配置供API Gateway使用
        routes_file = self.base_config_path.parent / "gateway_routes.json"
        with open(routes_file, 'w') as f:
            json.dump(routes, f, indent=2)

        logger.debug(f"Updated gateway routes: {len(routes)} active routes")

    async def _graceful_stop_via_api(self, port: int):
        """通过API优雅停止"""
        try:
            api_url = f"http://127.0.0.1:{port}"
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{api_url}/api/v1/stop",
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                logger.debug(f"Sent stop signal to FreqTrade on port {port}")
        except:
            pass  # 忽略错误，将通过强制停止处理

    async def _force_stop_process(self, process: subprocess.Popen):
        """强制停止进程"""
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, killing...")
                    process.kill()
                    process.wait()
        except Exception as e:
            logger.error(f"Error stopping process: {e}")

    async def _cleanup_failed_strategy(self, strategy_id: int):
        """清理失败的策略"""
        if strategy_id in self.strategy_processes:
            await self._force_stop_process(self.strategy_processes[strategy_id])
            del self.strategy_processes[strategy_id]

        if strategy_id in self.strategy_ports:
            # 释放端口回端口池
            released_port = self.strategy_ports[strategy_id]
            self.port_pool.add(released_port)
            logger.info(f"Cleanup: Released port {released_port} back to pool")
            del self.strategy_ports[strategy_id]

    async def _get_proxy_config(self, proxy_id: Optional[int], db = None) -> dict:
        """获取代理配置 - 从数据库查询健康的代理"""
        if not proxy_id or not db:
            logger.debug("No proxy configured or no database session available")
            return {}

        try:
            from sqlalchemy import select
            from models.proxy import Proxy

            # 查询指定的代理
            result = await db.execute(
                select(Proxy).where(Proxy.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()

            if not proxy:
                logger.warning(f"Proxy {proxy_id} not found in database")
                return {}

            # 检查代理是否可用
            if not proxy.is_active or not proxy.is_healthy:
                logger.warning(
                    f"Proxy {proxy_id} ({proxy.name}) is not available: "
                    f"active={proxy.is_active}, healthy={proxy.is_healthy}"
                )
                # 尝试查找备用代理
                result = await db.execute(
                    select(Proxy)
                    .where(Proxy.is_active == True)
                    .where(Proxy.is_healthy == True)
                    .order_by(Proxy.priority, Proxy.success_rate.desc())
                    .limit(1)
                )
                proxy = result.scalar_one_or_none()

                if not proxy:
                    logger.warning("No healthy backup proxy available, will use direct connection")
                    return {}
                else:
                    logger.info(f"Using backup proxy {proxy.id} ({proxy.name})")

            # 构建代理URL
            proxy_url = f"{proxy.proxy_type}://"

            # 添加认证信息（如果有）
            if proxy.username and proxy.password:
                proxy_url += f"{proxy.username}:{proxy.password}@"

            proxy_url += f"{proxy.host}:{proxy.port}"

            logger.info(f"Using proxy {proxy.id} ({proxy.name}): {proxy.proxy_type}://{proxy.host}:{proxy.port}")

            # 返回CCXT格式的代理配置
            return {
                "http": proxy_url,
                "https": proxy_url
            }

        except Exception as e:
            logger.error(f"Failed to get proxy configuration: {e}", exc_info=True)
            return {}
