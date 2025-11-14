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

            # 0. ⭐ 清理该策略的所有旧进程（防止重复进程）
            await self._cleanup_old_strategy_processes(strategy_id)

            # 1. 分配端口
            port = await self._allocate_port(strategy_id)
            logger.info(f"Allocated port {port} for strategy {strategy_id}")

            # 2. 生成配置文件（传递db session用于查询代理）
            config_file = await self._generate_config_file(strategy_config, port, db)
            logger.info(f"Generated config file for strategy {strategy_id}: {config_file}")

            # 3. 启动FreqTrade进程
            process = await self._start_freqtrade_process(config_file, strategy_id)
            logger.info(f"Started FreqTrade process for strategy {strategy_id} (PID: {process.pid})")

            # 4. 等待API就绪（传入process对象以检查进程存活性）
            await self._wait_for_api_ready(port, process)
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

    async def restart_strategy(self, strategy_id: int, db=None) -> bool:
        """重启指定策略"""
        try:
            logger.info(f"Restarting strategy {strategy_id}")

            # 1. 检查策略是否在运行
            if strategy_id not in self.strategy_processes:
                logger.warning(f"Strategy {strategy_id} is not running, cannot restart")
                return False

            # 2. 保存策略配置（需要从数据库读取）
            if db is None:
                from database.session import SessionLocal
                async with SessionLocal() as session:
                    from models.strategy import Strategy
                    from sqlalchemy import select
                    result = await session.execute(
                        select(Strategy).where(Strategy.id == strategy_id)
                    )
                    strategy = result.scalar_one_or_none()
                    if not strategy:
                        logger.error(f"Strategy {strategy_id} not found in database")
                        return False

                    strategy_config = {
                        "id": strategy.id,
                        "name": strategy.name,
                        "strategy_class": strategy.strategy_class,
                        "exchange": strategy.exchange,
                        "timeframe": strategy.timeframe,
                        "pair_whitelist": strategy.pair_whitelist,
                        "dry_run": strategy.dry_run,
                        "stake_amount": strategy.stake_amount,
                        "proxy_id": strategy.proxy_id
                    }
            else:
                from models.strategy import Strategy
                from sqlalchemy import select
                result = await db.execute(
                    select(Strategy).where(Strategy.id == strategy_id)
                )
                strategy = result.scalar_one_or_none()
                if not strategy:
                    logger.error(f"Strategy {strategy_id} not found in database")
                    return False

                strategy_config = {
                    "id": strategy.id,
                    "name": strategy.name,
                    "strategy_class": strategy.strategy_class,
                    "exchange": strategy.exchange,
                    "timeframe": strategy.timeframe,
                    "pair_whitelist": strategy.pair_whitelist,
                    "dry_run": strategy.dry_run,
                    "stake_amount": strategy.stake_amount,
                    "proxy_id": strategy.proxy_id
                }

            # 3. 停止策略
            stop_success = await self.stop_strategy(strategy_id)
            if not stop_success:
                logger.error(f"Failed to stop strategy {strategy_id} before restart")
                return False

            # 4. 等待一小段时间，确保资源完全释放
            await asyncio.sleep(2)

            # 5. 重新启动策略
            start_success = await self.create_strategy(strategy_config, db)
            if not start_success:
                logger.error(f"Failed to start strategy {strategy_id} after restart")
                return False

            logger.info(f"Strategy {strategy_id} restarted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to restart strategy {strategy_id}: {e}", exc_info=True)
            return False

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
        """
        检查单个策略的健康状态

        验证：
        1. 进程是否存活
        2. API是否响应
        3. 端口是否由正确的进程监听
        """
        if strategy_id not in self.strategy_processes:
            return {
                "strategy_id": strategy_id,
                "status": "not_found",
                "healthy": False,
                "message": "Strategy process not found in manager"
            }

        process = self.strategy_processes[strategy_id]
        port = self.strategy_ports.get(strategy_id)

        # 1. 检查进程是否运行
        process_running = process.poll() is None
        if not process_running:
            logger.warning(f"Strategy {strategy_id} process is dead (exit code: {process.returncode})")
            return {
                "strategy_id": strategy_id,
                "status": "process_dead",
                "healthy": False,
                "message": f"Process exited with code {process.returncode}",
                "port": port,
                "exit_code": process.returncode
            }

        # 2. 检查API是否响应
        if port:
            api_healthy = await self._check_api_health(port)
            if not api_healthy:
                logger.warning(f"Strategy {strategy_id} API not responding on port {port}")
                return {
                    "strategy_id": strategy_id,
                    "status": "api_unhealthy",
                    "healthy": False,
                    "message": f"FreqTrade API not responding on port {port}",
                    "port": port,
                    "process_id": process.pid
                }

            # 3. ⭐ 新增：验证端口是否由正确的进程监听
            port_owner = self._check_port_owner(port)
            if port_owner and port_owner != process.pid:
                logger.error(
                    f"Strategy {strategy_id} port conflict: "
                    f"port {port} is owned by process {port_owner}, not {process.pid}"
                )
                return {
                    "strategy_id": strategy_id,
                    "status": "port_conflict",
                    "healthy": False,
                    "message": f"Port {port} is owned by another process (PID: {port_owner})",
                    "port": port,
                    "expected_pid": process.pid,
                    "actual_pid": port_owner
                }

        # 4. 获取进程资源使用情况
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
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Cannot access process {process.pid} info: {e}")
            return {
                "strategy_id": strategy_id,
                "status": "process_inaccessible",
                "healthy": False,
                "message": f"Cannot access process information: {e}",
                "port": port
            }

    def _check_port_owner(self, port: int) -> Optional[int]:
        """
        检查端口的所有者进程ID

        Returns:
            int: 进程ID，如果端口未被占用则返回None
        """
        try:
            import socket
            # 尝试通过psutil查找监听该端口的进程
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN' and conn.laddr.port == port:
                    return conn.pid
            return None
        except Exception as e:
            logger.warning(f"Failed to check port {port} owner: {e}")
            return None

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

            # 必需字段：计价货币
            "stake_currency": "USDT",
            "stake_amount": strategy_config.get("stake_amount", 100),
            "max_open_trades": strategy_config.get("max_open_trades", 3),

            "exchange": {
                "name": strategy_config["exchange"],
                "key": "",
                "secret": "",
                "ccxt_config": {
                    "enableRateLimit": True,
                    "proxies": proxy_config,
                    "aiohttp_proxy": proxy_config.get("http") or proxy_config.get("https") if proxy_config else None
                },
                "pair_whitelist": strategy_config["pair_whitelist"],
                "pair_blacklist": strategy_config.get("pair_blacklist", [])
            },

            "pairlists": [{"method": "StaticPairList"}],

            # 价格配置
            "entry_pricing": {
                "price_side": "same",
                "use_order_book": True,
                "order_book_top": 1,
                "price_last_balance": 0.0,
                "check_depth_of_market": {
                    "enabled": False,
                    "bids_to_ask_delta": 1
                }
            },

            "exit_pricing": {
                "price_side": "same",
                "use_order_book": True,
                "order_book_top": 1
            },

            # 独立API端口配置
            "api_server": {
                "enabled": True,
                "listen_ip_address": "127.0.0.1",
                "listen_port": port,
                "username": "btc_watcher",
                "password": f"btc-watcher-pass-{strategy_config['id']}",
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

        # 读取配置文件获取代理设置
        import json
        with open(config_file, 'r') as f:
            config = json.load(f)

        # 准备环境变量（继承当前环境）
        env = os.environ.copy()

        # 如果配置了代理，设置环境变量
        proxies = config.get('exchange', {}).get('ccxt_config', {}).get('proxies', {})
        if proxies:
            if 'http' in proxies:
                env['HTTP_PROXY'] = proxies['http']
                env['http_proxy'] = proxies['http']
            if 'https' in proxies:
                env['HTTPS_PROXY'] = proxies['https']
                env['https_proxy'] = proxies['https']
            logger.info(f"Starting FreqTrade with proxy: {proxies}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        return process

    async def _wait_for_api_ready(self, port: int, process: subprocess.Popen, timeout: int = 30):
        """
        等待FreqTrade API就绪

        Args:
            port: API端口
            process: FreqTrade进程对象
            timeout: 超时时间（秒），默认30秒

        Raises:
            Exception: 如果进程退出或API超时未响应
        """
        start_time = asyncio.get_event_loop().time()
        api_url = f"http://127.0.0.1:{port}"

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # 1️⃣ 首先检查进程是否还存活
            if process.poll() is not None:
                # 进程已退出
                exit_code = process.returncode

                # 读取stderr获取错误信息
                stderr_output = ""
                try:
                    if process.stderr:
                        stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.warning(f"Failed to read stderr: {e}")

                # 提取关键错误信息
                error_summary = "Unknown error"
                if stderr_output:
                    # 提取最后几行重要错误
                    lines = stderr_output.strip().split('\n')
                    error_lines = [line for line in lines[-10:] if 'error' in line.lower() or 'exception' in line.lower()]
                    if error_lines:
                        error_summary = '\n'.join(error_lines[-3:])  # 最后3行错误
                    else:
                        error_summary = '\n'.join(lines[-3:])  # 最后3行输出

                logger.error(
                    f"FreqTrade process (port {port}) exited unexpectedly with code {exit_code}. "
                    f"Error: {error_summary[:500]}"
                )

                raise Exception(
                    f"FreqTrade process exited unexpectedly with code {exit_code}. "
                    f"Error: {error_summary[:500]}"
                )

            # 2️⃣ 检查API是否响应
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{api_url}/api/v1/ping",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info(f"✅ FreqTrade API on port {port} is ready (PID: {process.pid})")
                            return True
            except Exception as e:
                logger.debug(f"API not ready yet (port {port}): {e}")

            # 3️⃣ 等待2秒后重试
            await asyncio.sleep(2)

        # 4️⃣ 超时检查：最后再检查一次进程状态
        if process.poll() is not None:
            exit_code = process.returncode
            raise Exception(
                f"FreqTrade process exited during startup with code {exit_code}. "
                f"Check logs at {self.logs_path}/strategy_*.log"
            )

        # 5️⃣ 进程存活但API不响应
        logger.error(
            f"FreqTrade API on port {port} failed to start within {timeout}s. "
            f"Process is still running (PID: {process.pid}) but API is not responding."
        )
        raise Exception(
            f"FreqTrade API on port {port} failed to start within {timeout}s. "
            f"Process is still running (PID: {process.pid}) but API is not responding."
        )

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

    async def recover_running_strategies(self, db, max_retries: int = 2) -> dict:
        """
        启动时恢复数据库中状态为running的策略

        Args:
            db: 数据库session
            max_retries: 单个策略最大重试次数

        Returns:
            dict: 恢复结果统计
        """
        from sqlalchemy import select, update
        from models.strategy import Strategy

        logger.info("Starting strategy recovery process...")

        results = {
            "total_found": 0,
            "recovered": 0,
            "failed": 0,
            "reset": 0,
            "details": []
        }

        try:
            # 1. 查询所有运行中的策略
            stmt = select(Strategy).where(Strategy.status == 'running')
            result = await db.execute(stmt)
            running_strategies = result.scalars().all()

            results["total_found"] = len(running_strategies)
            logger.info(f"Found {results['total_found']} strategies in 'running' state")

            if not running_strategies:
                logger.info("No running strategies to recover")
                return results

            # 2. 逐个尝试恢复策略
            for strategy in running_strategies:
                strategy_id = strategy.id

                # ⭐ 跳过已经在 manager 中运行的策略（通过同步阶段注册的）
                if strategy_id in self.strategy_processes:
                    logger.info(f"Strategy {strategy_id} already running in manager (registered by sync), skipping recovery")
                    results["recovered"] += 1
                    results["details"].append({
                        "strategy_id": strategy_id,
                        "name": strategy.name,
                        "status": "already_running",
                        "retries": 0
                    })
                    continue

                logger.info(f"Attempting to recover strategy {strategy_id}: {strategy.name}")

                retry_count = 0
                recovered = False

                while retry_count < max_retries and not recovered:
                    try:
                        # 准备策略配置
                        strategy_config = {
                            "id": strategy.id,
                            "name": strategy.name,
                            "strategy_class": strategy.strategy_class,
                            "exchange": strategy.exchange,
                            "timeframe": strategy.timeframe,
                            "pair_whitelist": strategy.pair_whitelist,
                            "pair_blacklist": strategy.pair_blacklist,
                            "dry_run": strategy.dry_run,
                            "dry_run_wallet": strategy.dry_run_wallet,
                            "stake_amount": strategy.stake_amount,
                            "max_open_trades": strategy.max_open_trades,
                            "proxy_id": strategy.proxy_id
                        }

                        # 尝试创建策略
                        success = await self.create_strategy(strategy_config, db)

                        if success:
                            logger.info(f"✅ Successfully recovered strategy {strategy_id}")
                            results["recovered"] += 1
                            results["details"].append({
                                "strategy_id": strategy_id,
                                "name": strategy.name,
                                "status": "recovered",
                                "retries": retry_count
                            })
                            recovered = True
                        else:
                            retry_count += 1
                            if retry_count < max_retries:
                                logger.warning(f"Failed to recover strategy {strategy_id}, retry {retry_count}/{max_retries}")
                                await asyncio.sleep(2)  # 重试前等待

                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Error recovering strategy {strategy_id} (attempt {retry_count}/{max_retries}): {e}")
                        if retry_count < max_retries:
                            await asyncio.sleep(2)

                # 3. 如果所有重试都失败，重置状态为stopped
                if not recovered:
                    logger.warning(f"❌ Failed to recover strategy {strategy_id} after {max_retries} attempts, resetting to 'stopped'")
                    try:
                        stmt = update(Strategy).where(
                            Strategy.id == strategy_id
                        ).values(status='stopped')
                        await db.execute(stmt)
                        await db.commit()

                        results["failed"] += 1
                        results["reset"] += 1
                        results["details"].append({
                            "strategy_id": strategy_id,
                            "name": strategy.name,
                            "status": "failed_and_reset",
                            "retries": max_retries
                        })
                    except Exception as e:
                        logger.error(f"Failed to reset strategy {strategy_id} status: {e}")

            # 4. 日志摘要
            logger.info("="*50)
            logger.info("Strategy Recovery Summary:")
            logger.info(f"  Total strategies found: {results['total_found']}")
            logger.info(f"  Successfully recovered: {results['recovered']}")
            logger.info(f"  Failed and reset: {results['failed']}")
            logger.info("="*50)

            return results

        except Exception as e:
            logger.error(f"Critical error during strategy recovery: {e}", exc_info=True)
            results["error"] = str(e)
            return results

    async def reset_all_strategies_status(self, db) -> int:
        """
        将所有running状态的策略重置为stopped

        Args:
            db: 数据库session

        Returns:
            int: 重置的策略数量
        """
        from sqlalchemy import update
        from models.strategy import Strategy

        try:
            stmt = update(Strategy).where(
                Strategy.status == 'running'
            ).values(status='stopped')

            result = await db.execute(stmt)
            await db.commit()

            reset_count = result.rowcount
            logger.info(f"Reset {reset_count} strategies to 'stopped' status")
            return reset_count

        except Exception as e:
            logger.error(f"Failed to reset strategy statuses: {e}", exc_info=True)
            await db.rollback()
            return 0

    def scan_freqtrade_processes(self) -> List[Dict]:
        """
        扫描系统中所有运行的 FreqTrade 进程

        Returns:
            List[Dict]: 进程信息列表，每个元素包含:
                - pid: 进程ID
                - strategy_id: 策略ID（从配置文件路径提取）
                - config_file: 配置文件路径
                - log_file: 日志文件路径
                - port: API端口（如果正在监听）
                - is_healthy: 是否健康（有API端口）
        """
        processes = []

        try:
            # 遍历所有进程，查找 freqtrade 进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if not cmdline:
                        continue

                    # 检查是否是 freqtrade trade 命令
                    if 'freqtrade' in ' '.join(cmdline) and 'trade' in cmdline:
                        # 提取配置文件路径
                        config_file = None
                        log_file = None

                        for i, arg in enumerate(cmdline):
                            if arg == '--config' and i + 1 < len(cmdline):
                                config_file = cmdline[i + 1]
                            elif arg == '--logfile' and i + 1 < len(cmdline):
                                log_file = cmdline[i + 1]

                        if not config_file:
                            continue

                        # 从配置文件路径提取策略ID
                        # 格式: /path/to/freqtrade_configs/strategy_10.json
                        import re
                        match = re.search(r'strategy_(\d+)\.json', config_file)
                        if not match:
                            continue

                        strategy_id = int(match.group(1))

                        # 检查进程是否监听端口
                        port = None
                        is_healthy = False

                        try:
                            # 查找该进程监听的端口
                            connections = proc.connections(kind='inet')
                            for conn in connections:
                                if conn.status == 'LISTEN' and conn.laddr.ip == '127.0.0.1':
                                    port = conn.laddr.port
                                    is_healthy = True
                                    break
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            pass

                        processes.append({
                            'pid': proc.info['pid'],
                            'strategy_id': strategy_id,
                            'config_file': config_file,
                            'log_file': log_file,
                            'port': port,
                            'is_healthy': is_healthy
                        })

                        logger.debug(f"Found FreqTrade process: PID={proc.info['pid']}, "
                                   f"Strategy={strategy_id}, Port={port}, Healthy={is_healthy}")

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            logger.info(f"Scanned system: found {len(processes)} FreqTrade processes")
            return processes

        except Exception as e:
            logger.error(f"Error scanning FreqTrade processes: {e}", exc_info=True)
            return []

    async def sync_strategy_status(self, db) -> dict:
        """
        同步数据库状态与实际运行的进程状态

        这个方法会：
        1. 扫描所有实际运行的 FreqTrade 进程
        2. 对比数据库中的状态
        3. 清理僵尸进程（运行但没有API端口）
        4. 更新数据库状态以匹配实际情况
        5. 将健康的孤儿进程注册到 manager

        Args:
            db: 数据库session

        Returns:
            dict: 同步结果统计
        """
        from sqlalchemy import select, update
        from models.strategy import Strategy

        logger.info("="*60)
        logger.info("Starting automatic strategy status synchronization...")
        logger.info("="*60)

        results = {
            "scanned_processes": 0,
            "orphan_processes": 0,
            "zombie_processes": 0,
            "synced_to_running": 0,
            "synced_to_stopped": 0,
            "registered_orphans": 0,
            "killed_zombies": 0,
            "errors": [],
            "details": []
        }

        try:
            # 1. 扫描所有 FreqTrade 进程
            running_processes = self.scan_freqtrade_processes()
            results["scanned_processes"] = len(running_processes)
            logger.info(f"Found {len(running_processes)} FreqTrade processes running on system")

            # 2. 查询数据库中所有策略
            stmt = select(Strategy)
            result = await db.execute(stmt)
            all_strategies = {s.id: s for s in result.scalars().all()}
            logger.info(f"Found {len(all_strategies)} strategies in database")

            # 3. 分析每个运行中的进程
            process_map = {p['strategy_id']: p for p in running_processes}

            for proc_info in running_processes:
                strategy_id = proc_info['strategy_id']
                pid = proc_info['pid']
                port = proc_info['port']
                is_healthy = proc_info['is_healthy']

                # 检查是否是孤儿进程（数据库显示stopped或error但实际在运行）
                db_strategy = all_strategies.get(strategy_id)
                if not db_strategy:
                    logger.warning(f"Process PID={pid} for strategy {strategy_id} found, "
                                 f"but strategy not in database")
                    results["errors"].append(f"Strategy {strategy_id} not found in database")
                    continue

                is_orphan = db_strategy.status in ['stopped', 'error']

                # 3a. 处理僵尸进程（运行但没有API端口）
                if not is_healthy:
                    logger.warning(f"🧟 Zombie process detected: Strategy {strategy_id}, PID={pid}, "
                                 f"no API port listening")
                    results["zombie_processes"] += 1

                    try:
                        # 杀死僵尸进程
                        proc = psutil.Process(pid)
                        proc.terminate()
                        proc.wait(timeout=10)
                        logger.info(f"✅ Killed zombie process PID={pid} for strategy {strategy_id}")
                        results["killed_zombies"] += 1
                        results["details"].append({
                            "strategy_id": strategy_id,
                            "action": "killed_zombie",
                            "pid": pid,
                            "reason": "No API port listening"
                        })
                    except Exception as e:
                        logger.error(f"Failed to kill zombie process PID={pid}: {e}")
                        results["errors"].append(f"Failed to kill zombie PID={pid}: {e}")

                    continue

                # 3b. 处理孤儿进程（健康但数据库显示stopped）
                if is_orphan:
                    logger.info(f"🔍 Orphan process detected: Strategy {strategy_id}, "
                              f"PID={pid}, Port={port}, DB status='{db_strategy.status}'")
                    results["orphan_processes"] += 1

                    # 验证API是否真的可用
                    api_ok = await self._check_api_health(port)
                    if api_ok:
                        # 注册到 manager
                        try:
                            # 创建 Popen 对象的替代品（因为我们没有实际的Popen对象）
                            # 我们需要修改 manager 的数据结构来存储这些信息
                            class ExternalProcess:
                                def __init__(self, pid):
                                    self.pid = pid
                                    self._proc = psutil.Process(pid)

                                def poll(self):
                                    try:
                                        if self._proc.is_running():
                                            return None  # Still running
                                        return self._proc.returncode if hasattr(self._proc, 'returncode') else 0
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        return -1  # Process dead

                            # 注册到 manager
                            self.strategy_processes[strategy_id] = ExternalProcess(pid)
                            self.strategy_ports[strategy_id] = port

                            # 从端口池中移除该端口
                            if port in self.port_pool:
                                self.port_pool.remove(port)

                            # 更新数据库状态
                            stmt = update(Strategy).where(
                                Strategy.id == strategy_id
                            ).values(
                                status='running',
                                process_id=pid,
                                port=port
                            )
                            await db.execute(stmt)
                            await db.commit()

                            logger.info(f"✅ Registered orphan process: Strategy {strategy_id}, "
                                      f"PID={pid}, Port={port}")
                            results["registered_orphans"] += 1
                            results["synced_to_running"] += 1
                            results["details"].append({
                                "strategy_id": strategy_id,
                                "action": "registered_orphan",
                                "pid": pid,
                                "port": port,
                                "old_status": "stopped",
                                "new_status": "running"
                            })

                        except Exception as e:
                            logger.error(f"Failed to register orphan process {strategy_id}: {e}")
                            results["errors"].append(f"Failed to register orphan {strategy_id}: {e}")
                    else:
                        logger.warning(f"Orphan process {strategy_id} has port but API unhealthy, "
                                     f"treating as zombie")
                        results["zombie_processes"] += 1
                        # 杀死不健康的孤儿进程
                        try:
                            proc = psutil.Process(pid)
                            proc.terminate()
                            proc.wait(timeout=10)
                            logger.info(f"✅ Killed unhealthy orphan process PID={pid}")
                            results["killed_zombies"] += 1
                        except Exception as e:
                            logger.error(f"Failed to kill unhealthy process PID={pid}: {e}")

                # 3c. 进程健康且数据库状态为 running - 需要注册到 manager
                elif db_strategy.status == 'running':
                    # 检查是否需要注册到 manager（PID不匹配说明是孤儿进程）
                    pid_mismatch = db_strategy.process_id != pid
                    port_mismatch = db_strategy.port != port
                    needs_registration = strategy_id not in self.strategy_processes

                    if pid_mismatch or port_mismatch or needs_registration:
                        logger.info(f"Re-registering running strategy {strategy_id}: "
                                  f"PID {db_strategy.process_id}->{pid}, "
                                  f"Port {db_strategy.port}->{port}, "
                                  f"In manager: {not needs_registration}")

                        # 注册到 manager（如果还没有）
                        if needs_registration:
                            class ExternalProcess:
                                def __init__(self, pid):
                                    self.pid = pid
                                    self._proc = psutil.Process(pid)

                                def poll(self):
                                    try:
                                        if self._proc.is_running():
                                            return None  # Still running
                                        return self._proc.returncode if hasattr(self._proc, 'returncode') else 0
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        return -1  # Process dead

                            self.strategy_processes[strategy_id] = ExternalProcess(pid)
                            self.strategy_ports[strategy_id] = port

                            # 从端口池中移除该端口
                            if port in self.port_pool:
                                self.port_pool.remove(port)

                            logger.info(f"✅ Registered running strategy {strategy_id} to manager")

                        # 更新数据库元数据
                        stmt = update(Strategy).where(
                            Strategy.id == strategy_id
                        ).values(
                            process_id=pid,
                            port=port
                        )
                        await db.execute(stmt)
                        await db.commit()

                        results["details"].append({
                            "strategy_id": strategy_id,
                            "action": "re_registered_running",
                            "old_pid": db_strategy.process_id,
                            "new_pid": pid,
                            "old_port": db_strategy.port,
                            "new_port": port
                        })

            # 4. 检查数据库中标记为running但实际未运行的策略
            for strategy_id, strategy in all_strategies.items():
                if strategy.status == 'running' and strategy_id not in process_map:
                    logger.warning(f"Strategy {strategy_id} marked as 'running' in DB but no process found")

                    # 重置为stopped
                    stmt = update(Strategy).where(
                        Strategy.id == strategy_id
                    ).values(status='stopped')
                    await db.execute(stmt)
                    await db.commit()

                    # 从 manager 中清理
                    if strategy_id in self.strategy_processes:
                        del self.strategy_processes[strategy_id]
                    if strategy_id in self.strategy_ports:
                        port = self.strategy_ports[strategy_id]
                        self.port_pool.add(port)
                        del self.strategy_ports[strategy_id]

                    logger.info(f"✅ Reset strategy {strategy_id} status to 'stopped'")
                    results["synced_to_stopped"] += 1
                    results["details"].append({
                        "strategy_id": strategy_id,
                        "action": "synced_to_stopped",
                        "reason": "No running process found"
                    })

            # 5. 输出同步摘要
            logger.info("="*60)
            logger.info("Strategy Status Synchronization Summary:")
            logger.info(f"  Scanned processes: {results['scanned_processes']}")
            logger.info(f"  Orphan processes found: {results['orphan_processes']}")
            logger.info(f"  Zombie processes found: {results['zombie_processes']}")
            logger.info(f"  Registered orphans: {results['registered_orphans']}")
            logger.info(f"  Killed zombies: {results['killed_zombies']}")
            logger.info(f"  Synced to running: {results['synced_to_running']}")
            logger.info(f"  Synced to stopped: {results['synced_to_stopped']}")
            logger.info(f"  Errors: {len(results['errors'])}")
            logger.info("="*60)

            return results

        except Exception as e:
            logger.error(f"Critical error during status synchronization: {e}", exc_info=True)
            results["errors"].append(f"Critical error: {e}")
            return results

    async def _cleanup_old_strategy_processes(self, strategy_id: int):
        """
        清理指定策略的所有旧进程

        这个方法在启动新策略前调用，确保不会有重复进程

        Args:
            strategy_id: 策略ID
        """
        try:
            # 1. 从 manager 中清理（如果存在）
            if strategy_id in self.strategy_processes:
                logger.info(f"Cleaning up strategy {strategy_id} from manager")
                old_process = self.strategy_processes[strategy_id]

                # 尝试优雅停止
                try:
                    if old_process.poll() is None:  # Process still running
                        old_process.terminate()
                        try:
                            old_process.wait(timeout=5)
                        except:
                            old_process.kill()
                            old_process.wait()
                except Exception as e:
                    logger.warning(f"Error stopping old process from manager: {e}")

                del self.strategy_processes[strategy_id]

            # 2. 释放端口
            if strategy_id in self.strategy_ports:
                port = self.strategy_ports[strategy_id]
                self.port_pool.add(port)
                logger.info(f"Released port {port} back to pool")
                del self.strategy_ports[strategy_id]

            # 3. 扫描系统中该策略的所有进程并清理
            all_processes = self.scan_freqtrade_processes()
            strategy_processes = [p for p in all_processes if p['strategy_id'] == strategy_id]

            if strategy_processes:
                logger.warning(f"Found {len(strategy_processes)} orphan processes for strategy {strategy_id}, cleaning up...")
                for proc_info in strategy_processes:
                    pid = proc_info['pid']
                    try:
                        proc = psutil.Process(pid)
                        proc.terminate()
                        proc.wait(timeout=5)
                        logger.info(f"✅ Killed orphan process PID={pid} for strategy {strategy_id}")
                    except psutil.TimeoutExpired:
                        try:
                            proc.kill()
                            proc.wait()
                            logger.info(f"✅ Force killed orphan process PID={pid} for strategy {strategy_id}")
                        except Exception as e:
                            logger.error(f"Failed to kill orphan process PID={pid}: {e}")
                    except psutil.NoSuchProcess:
                        logger.debug(f"Process PID={pid} already terminated")
                    except Exception as e:
                        logger.error(f"Error cleaning up process PID={pid}: {e}")

            logger.info(f"✅ Old processes cleanup completed for strategy {strategy_id}")

        except Exception as e:
            logger.error(f"Error during old processes cleanup for strategy {strategy_id}: {e}", exc_info=True)
            # 即使清理失败也继续，不阻止新进程启动

