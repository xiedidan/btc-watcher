# BTC Watcher 技术实现细节

## 基于用户确认的技术方案

### 🔧 核心技术决策确认

1. **FreqTrade集成**: Docker代码集成 (FreqTrade 2025.8)
2. **数据保留**: 信号和通知数据永久保存
3. **监控频率**: 系统状态30秒，策略状态30秒
4. **配置管理**: 通过配置文件统一管理系统参数
5. **版本管理**: 用户手动触发升级
6. **安全级别**: 个人使用级别安全措施

---

## 1. FreqTrade反向代理集成架构

### 1.1 架构设计原则

**反向代理统一端口模式**：
- **内部多端口**: 每个策略运行独立的FreqTrade实例，使用独立端口
- **外部统一端口**: 通过API Gateway统一路由到8080端口
- **进程隔离**: 符合FreqTrade原生设计，每个策略独立进程
- **故障隔离**: 单个策略故障不影响其他策略运行

```
┌─────────────────────────────────────────────────────────────┐
│                    BTC Watcher API                          │
│                   :8000 (主服务)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│             FreqTrade API Gateway                          │
│                  :8080 (统一入口)                           │
│          路由规则: /api/strategy/{id}/...                   │
└─────────┬───┬───┬───┬───────────────────────────────────────┘
          │   │   │   │
┌─────────▼───▼───▼───▼───────────────────────────────────────┐
│ FreqTrade策略实例集群 (独立进程 + 独立端口)                   │
├─────────────────────────────────────────────────────────────┤
│ 策略1: MA_Cross_BTC     │  :8081  │  BTC/USDT              │
│ 策略2: RSI_ETH          │  :8082  │  ETH/USDT              │
│ 策略3: Custom_SOL       │  :8083  │  SOL/USDT              │
│ 策略4: Bollinger_ADA    │  :8084  │  ADA/USDT              │
│ 策略5: MACD_DOT         │  :8085  │  DOT/USDT              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 修正的FreqTrade管理器

```python
# backend/core/freqtrade_manager.py
import subprocess
import psutil
import json
import os
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FreqTradeGatewayManager:
    """FreqTrade网关管理器 - 反向代理模式"""

    def __init__(self):
        self.strategy_processes: Dict[int, subprocess.Popen] = {}
        self.strategy_ports: Dict[int, int] = {}  # strategy_id -> port
        self.freqtrade_version = "2025.8"
        self.gateway_port = 8080  # 统一网关端口
        self.base_port = 8081  # FreqTrade实例起始端口
        self.max_port = 9080   # FreqTrade实例最大端口 (999个端口: 8081-9080)
        self.max_strategies = 999  # 最大并发策略数
        self.base_config_path = "/app/freqtrade_configs"
        self.strategies_path = "/app/user_data/strategies"
        self.port_pool = set(range(self.base_port, self.max_port + 1))  # 可用端口池

    async def create_strategy(self, strategy_config: dict) -> bool:
        """创建并启动新策略"""
        strategy_id = strategy_config["id"]

        try:
            # 1. 分配端口
            port = await self._allocate_port(strategy_id)

            # 2. 生成配置文件
            config_file = await self._generate_config_file(strategy_config, port)

            # 3. 启动FreqTrade进程
            process = await self._start_freqtrade_process(config_file, strategy_id)

            # 4. 等待API就绪
            await self._wait_for_api_ready(port)

            # 5. 保存进程和端口信息
            self.strategy_processes[strategy_id] = process
            self.strategy_ports[strategy_id] = port

            # 6. 更新API Gateway路由
            await self._update_gateway_routes()

            logger.info(f"Strategy {strategy_id} started on port {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to create strategy {strategy_id}: {e}")
            await self._cleanup_failed_strategy(strategy_id)
            return False

    async def stop_strategy(self, strategy_id: int) -> bool:
        """停止指定策略"""
        try:
            if strategy_id not in self.strategy_processes:
                return True

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

            logger.info(f"Strategy {strategy_id} stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
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

    async def _allocate_port(self, strategy_id: int) -> int:
        """为策略分配端口 - 支持999个并发策略"""
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

    async def _generate_config_file(self, strategy_config: dict, port: int) -> str:
        """生成FreqTrade配置文件"""
        config = {
            "strategy": strategy_config["strategy_class"],
            "strategy_path": self.strategies_path,
            "timeframe": strategy_config["timeframe"],
            "dry_run": True,
            "dry_run_wallet": 1000,

            "exchange": {
                "name": strategy_config["exchange"],
                "key": "",
                "secret": "",
                "ccxt_config": {
                    "enableRateLimit": True,
                    "proxies": self._get_proxy_config(strategy_config.get("proxy_id"))
                },
                "pair_whitelist": strategy_config["pair_whitelist"],
                "pair_blacklist": []
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
        config_file = f"{self.base_config_path}/strategy_{strategy_config['id']}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return config_file

    async def _start_freqtrade_process(self, config_file: str, strategy_id: int) -> subprocess.Popen:
        """启动FreqTrade进程"""
        cmd = [
            "freqtrade", "trade",
            "--config", config_file,
            "--logfile", f"/app/logs/strategy_{strategy_id}.log"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        return process

    async def _wait_for_api_ready(self, port: int, timeout: int = 60):
        """等待FreqTrade API就绪"""
        start_time = asyncio.get_event_loop().time()
        api_url = f"http://127.0.0.1:{port}"

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{api_url}/api/v1/ping",
                                         timeout=aiohttp.ClientTimeout(total=5)) as response:
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
            routes[strategy_id] = {
                "upstream": f"http://127.0.0.1:{port}",
                "health_check": f"http://127.0.0.1:{port}/api/v1/ping"
            }

        # 保存路由配置供API Gateway使用
        routes_file = "/app/gateway_routes.json"
        with open(routes_file, 'w') as f:
            json.dump(routes, f, indent=2)

    async def get_strategy_status(self, strategy_id: int) -> dict:
        """获取策略状态"""
        if strategy_id not in self.strategy_processes:
            return {"status": "not_found", "message": f"Strategy {strategy_id} not found"}

        try:
            # 1. 进程状态
            process = self.strategy_processes[strategy_id]
            port = self.strategy_ports.get(strategy_id)

            basic_status = await self._get_process_status(process)

            if basic_status["status"] != "running" or not port:
                return basic_status

            # 2. FreqTrade API状态
            detailed_status = await self._get_freqtrade_status(port)

            return {
                "strategy_id": strategy_id,
                "port": port,
                "process_status": basic_status,
                "freqtrade_status": detailed_status
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _get_process_status(self, process: subprocess.Popen) -> dict:
        """获取进程状态"""
        try:
            if process.poll() is None:
                proc_info = psutil.Process(process.pid)
                return {
                    "status": "running",
                    "pid": process.pid,
                    "cpu_percent": proc_info.cpu_percent(),
                    "memory_mb": proc_info.memory_info().rss / 1024 / 1024,
                    "uptime_seconds": (psutil.time.time() - proc_info.create_time())
                }
            else:
                return {"status": "stopped", "exit_code": process.returncode}
        except psutil.NoSuchProcess:
            return {"status": "error", "error": "Process not found"}

    async def _get_freqtrade_status(self, port: int) -> dict:
        """通过API获取FreqTrade状态"""
        try:
            api_url = f"http://127.0.0.1:{port}"
            async with aiohttp.ClientSession() as session:
                status_data = {}

                # 获取各种状态信息
                endpoints = {
                    "status": "/api/v1/status",
                    "profit": "/api/v1/profit",
                    "trades": "/api/v1/trades",
                    "balance": "/api/v1/balance",
                    "logs": "/api/v1/logs?limit=50"
                }

                for key, endpoint in endpoints.items():
                    try:
                        async with session.get(f"{api_url}{endpoint}",
                                             timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status == 200:
                                status_data[key] = await response.json()
                    except Exception as e:
                        status_data[key] = {"error": str(e)}

                return status_data

        except Exception as e:
            return {"error": f"Failed to fetch FreqTrade status: {str(e)}"}

    async def get_all_strategies_status(self) -> Dict[int, dict]:
        """获取所有策略状态"""
        all_status = {}

        for strategy_id in self.strategy_processes.keys():
            all_status[strategy_id] = await self.get_strategy_status(strategy_id)

        return all_status

    async def execute_strategy_command(self, strategy_id: int, command: str, params: dict = None) -> dict:
        """执行策略命令"""
        if strategy_id not in self.strategy_processes:
            return {"error": "Strategy not found"}

        port = self.strategy_ports.get(strategy_id)
        if not port:
            return {"error": "Strategy port not found"}

        try:
            api_url = f"http://127.0.0.1:{port}"
            async with aiohttp.ClientSession() as session:
                if command == "start":
                    async with session.post(f"{api_url}/api/v1/start") as response:
                        return await response.json()

                elif command == "stop":
                    async with session.post(f"{api_url}/api/v1/stop") as response:
                        return await response.json()

                elif command == "reload_config":
                    async with session.post(f"{api_url}/api/v1/reload_config") as response:
                        return await response.json()

                else:
                    return {"error": f"Unknown command: {command}"}

        except Exception as e:
            return {"error": f"Failed to execute command: {str(e)}"}

    async def _graceful_stop_via_api(self, port: int):
        """通过API优雅停止"""
        try:
            api_url = f"http://127.0.0.1:{port}"
            async with aiohttp.ClientSession() as session:
                await session.post(f"{api_url}/api/v1/stop",
                                 timeout=aiohttp.ClientTimeout(total=30))
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
                    process.kill()
                    process.wait()
        except:
            pass

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

    async def get_available_strategies(self) -> List[dict]:
        """获取所有可用策略列表"""
        # 从数据库获取策略列表
        # 这里返回示例数据，实际应该从数据库查询
        return []

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

    def _get_proxy_config(self, proxy_id: Optional[int]) -> dict:
        """获取代理配置"""
        if not proxy_id:
            return {}
        return {
            "http": "socks5://proxy.example.com:1080",
            "https": "socks5://proxy.example.com:1080"
        }
```

### 1.4 API Gateway实现

```python
# backend/core/api_gateway.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import aiohttp
import json
import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FreqTradeAPIGateway:
    """FreqTrade API网关 - 统一端口路由管理"""

    def __init__(self, gateway_port: int = 8080):
        self.gateway_port = gateway_port
        self.app = FastAPI(title="FreqTrade API Gateway")
        self.routes_config = {}  # strategy_id -> upstream_config
        self.setup_routes()

    def setup_routes(self):
        """设置API Gateway路由规则"""

        # 1. 策略特定路由: /api/strategy/{strategy_id}/*
        @self.app.api_route("/api/strategy/{strategy_id:int}/{path:path}",
                           methods=["GET", "POST", "PUT", "DELETE"])
        async def strategy_proxy(strategy_id: int, path: str, request: Request):
            return await self._route_to_strategy(strategy_id, path, request)

        # 2. 管理路由: 获取所有策略状态
        @self.app.get("/api/strategies/status")
        async def get_all_strategies_status():
            return await self._get_all_strategies_status()

        # 3. 健康检查路由
        @self.app.get("/api/gateway/health")
        async def gateway_health():
            return await self._gateway_health_check()

        # 4. 路由配置更新
        @self.app.post("/api/gateway/routes/reload")
        async def reload_routes():
            return await self._reload_routes_config()

    async def _route_to_strategy(self, strategy_id: int, path: str, request: Request):
        """将请求路由到指定策略实例"""
        try:
            # 1. 检查策略是否存在
            if strategy_id not in self.routes_config:
                raise HTTPException(
                    status_code=404,
                    detail=f"Strategy {strategy_id} not found"
                )

            # 2. 获取上游服务地址
            upstream_config = self.routes_config[strategy_id]
            upstream_url = upstream_config["upstream"]

            # 3. 构建目标URL
            target_url = f"{upstream_url}/api/v1/{path}"

            # 4. 获取请求体数据
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()

            # 5. 转发请求到FreqTrade实例
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=dict(request.headers),
                    data=body,
                    params=dict(request.query_params),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    # 6. 返回响应
                    response_data = await response.text()
                    return JSONResponse(
                        content=json.loads(response_data) if response_data else {},
                        status_code=response.status,
                        headers=dict(response.headers)
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Upstream connection error for strategy {strategy_id}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Strategy {strategy_id} service unavailable"
            )
        except Exception as e:
            logger.error(f"Gateway routing error: {e}")
            raise HTTPException(status_code=500, detail="Gateway internal error")

    async def _get_all_strategies_status(self):
        """获取所有策略状态汇总"""
        all_status = {}

        for strategy_id, config in self.routes_config.items():
            try:
                # 并行获取所有策略状态
                upstream_url = config["upstream"]
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{upstream_url}/api/v1/status",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            status_data = await response.json()
                            all_status[strategy_id] = {
                                "status": "healthy",
                                "data": status_data,
                                "upstream": upstream_url
                            }
                        else:
                            all_status[strategy_id] = {
                                "status": "error",
                                "error": f"HTTP {response.status}",
                                "upstream": upstream_url
                            }
            except Exception as e:
                all_status[strategy_id] = {
                    "status": "unreachable",
                    "error": str(e),
                    "upstream": config.get("upstream", "unknown")
                }

        return {
            "gateway_status": "running",
            "total_strategies": len(self.routes_config),
            "strategies": all_status,
            "timestamp": asyncio.get_event_loop().time()
        }

    async def _gateway_health_check(self):
        """API Gateway健康检查"""
        healthy_count = 0
        total_count = len(self.routes_config)

        # 检查所有上游服务
        for strategy_id, config in self.routes_config.items():
            try:
                upstream_url = config["health_check"]
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        upstream_url,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            healthy_count += 1
            except:
                pass

        health_score = (healthy_count / total_count * 100) if total_count > 0 else 100

        return {
            "status": "healthy" if health_score >= 80 else "degraded",
            "health_score": health_score,
            "healthy_strategies": healthy_count,
            "total_strategies": total_count,
            "gateway_port": self.gateway_port,
            "routes_loaded": len(self.routes_config)
        }

    async def _reload_routes_config(self):
        """重新加载路由配置"""
        try:
            # 从文件加载路由配置
            routes_file = "/app/gateway_routes.json"
            with open(routes_file, 'r') as f:
                self.routes_config = json.load(f)

            logger.info(f"Reloaded {len(self.routes_config)} routes")
            return {
                "status": "success",
                "routes_count": len(self.routes_config),
                "message": "Routes configuration reloaded successfully"
            }
        except Exception as e:
            logger.error(f"Failed to reload routes: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def start_gateway(self):
        """启动API Gateway"""
        import uvicorn

        # 初始加载路由配置
        await self._reload_routes_config()

        # 启动Gateway服务
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.gateway_port,
            log_level="info"
        )
        server = uvicorn.Server(config)

        logger.info(f"Starting FreqTrade API Gateway on port {self.gateway_port}")
        await server.serve()
```

### 1.5 增强的信号接收和API集成

```python
# backend/api/v1/signals.py
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
import asyncio

router = APIRouter()

class FreqTradeSignal(BaseModel):
    """FreqTrade信号数据模型"""
    strategy: str
    pair: str
    action: str  # buy, sell, hold
    current_rate: float
    profit: float
    open_date: str
    close_date: Optional[str]
    trade_id: Optional[int]

    # 自定义指标数据
    indicators: dict = {}
    metadata: dict = {}

@router.post("/webhook/{strategy_id}")
async def receive_freqtrade_signal(
    strategy_id: int = Path(..., description="策略ID"),
    signal: FreqTradeSignal
):
    """接收指定策略的FreqTrade信号"""
    try:
        # 1. 解析信号数据并添加策略ID
        processed_signal = await process_signal_data(signal, strategy_id)

        # 2. 计算信号强度 (基于策略自定义逻辑)
        signal_strength = await calculate_signal_strength(processed_signal)

        # 3. 存储到数据库
        await save_signal_to_database(processed_signal)

        # 4. 实时推送到WebSocket
        await broadcast_signal_update(processed_signal)

        # 5. 触发通知 (根据强度阈值)
        await trigger_notifications_if_needed(processed_signal)

        return {"status": "success", "signal_id": processed_signal["id"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal processing failed: {str(e)}")

# backend/api/v1/strategies.py - 更新版本
from fastapi import APIRouter, HTTPException, Depends
from core.freqtrade_manager import FreqTradeGatewayManager
from core.api_gateway import FreqTradeAPIGateway

router = APIRouter()

@router.get("/strategies/{strategy_id}/status/detailed")
async def get_strategy_detailed_status(
    strategy_id: int,
    ft_manager: FreqTradeGatewayManager = Depends(),
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """获取策略详细状态（通过API Gateway）"""
    try:
        # 检查策略是否运行
        strategy_status = await ft_manager.get_strategy_status(strategy_id)

        if strategy_status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Strategy not found")

        # 通过API Gateway获取详细信息
        detailed_data = await api_gateway._route_to_strategy(
            strategy_id, "status", None
        )

        return {
            "strategy_id": strategy_id,
            "basic_status": strategy_status,
            "detailed_data": detailed_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/gateway/status")
async def get_gateway_status(
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """获取API Gateway状态和所有策略汇总"""
    try:
        gateway_status = await api_gateway._gateway_health_check()
        all_strategies = await api_gateway._get_all_strategies_status()

        return {
            "gateway": gateway_status,
            "strategies": all_strategies,
            "summary": {
                "total_strategies": gateway_status["total_strategies"],
                "healthy_strategies": gateway_status["healthy_strategies"],
                "health_percentage": gateway_status["health_score"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/start")
async def start_strategy(
    strategy_id: int,
    ft_manager: FreqTradeGatewayManager = Depends()
):
    """启动策略（创建新FreqTrade实例）"""
    try:
        # 获取策略配置
        strategy_config = await get_strategy_config(strategy_id)

        # 启动策略实例
        success = await ft_manager.create_strategy(strategy_config)

        if success:
            # 更新数据库状态
            await update_strategy_status(strategy_id, "running")

            return {
                "status": "success",
                "strategy_id": strategy_id,
                "message": f"Strategy {strategy_id} started successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start strategy")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: int,
    ft_manager: FreqTradeGatewayManager = Depends()
):
    """停止策略"""
    try:
        success = await ft_manager.stop_strategy(strategy_id)

        if success:
            # 更新数据库状态
            await update_strategy_status(strategy_id, "stopped")

            return {
                "status": "success",
                "strategy_id": strategy_id,
                "message": "Strategy stopped successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop strategy")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/commands/{command}")
async def execute_strategy_command(
    strategy_id: int,
    command: str,
    params: dict = None,
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """执行策略命令（通过API Gateway）"""
    try:
        # 构建命令路径
        if command in ["start", "stop", "reload_config"]:
            path = f"v1/{command}"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown command: {command}")

        # 通过API Gateway转发命令
        result = await api_gateway._route_to_strategy(strategy_id, path, None)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}/logs")
async def get_strategy_logs(
    strategy_id: int,
    limit: int = 100,
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """获取策略日志（通过API Gateway）"""
    try:
        # 通过API Gateway获取日志
        logs_data = await api_gateway._route_to_strategy(
            strategy_id, f"logs?limit={limit}", None
        )

        return {
            "strategy_id": strategy_id,
            "logs": logs_data,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/overview")
async def get_strategies_overview(
    ft_manager: FreqTradeGatewayManager = Depends(),
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """获取所有策略状态概览"""
    try:
        # 获取Gateway汇总状态
        gateway_summary = await api_gateway._get_all_strategies_status()

        # 获取所有可用策略
        available_strategies = await ft_manager.get_available_strategies()

        # 组合返回数据
        strategies_with_status = []
        for strategy in available_strategies:
            strategy_id = strategy["id"]
            gateway_status = gateway_summary["strategies"].get(str(strategy_id), {})

            strategies_with_status.append({
                **strategy,
                "runtime_status": gateway_status.get("status", "unknown"),
                "is_running": gateway_status.get("status") == "healthy",
                "upstream_url": gateway_status.get("upstream"),
                "last_check": gateway_summary.get("timestamp")
            })

        return {
            "summary": {
                "total_strategies": len(available_strategies),
                "running_strategies": gateway_summary["total_strategies"],
                "healthy_strategies": len([s for s in gateway_summary["strategies"].values()
                                         if s.get("status") == "healthy"]),
                "gateway_status": gateway_summary["gateway_status"]
            },
            "strategies": strategies_with_status,
            "gateway_info": {
                "port": api_gateway.gateway_port,
                "routes_count": len(api_gateway.routes_config),
                "last_update": gateway_summary.get("timestamp")
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 1.6 监控服务的多实例集成

```python
# backend/services/monitoring_service.py - 更新版本
import asyncio
import time
import aiohttp
from typing import Dict
import psutil
import redis.asyncio as redis
from core.freqtrade_manager import FreqTradeGatewayManager
from core.api_gateway import FreqTradeAPIGateway
from core.config_manager import config_manager

class EnhancedMonitoringService:
    """增强的监控服务 - 支持FreqTrade多实例架构"""

    def __init__(self):
        self.redis_client = None
        self.freqtrade_manager: FreqTradeGatewayManager = None
        self.api_gateway: FreqTradeAPIGateway = None
        self.monitoring_tasks = {}
        self.config = config_manager.get_monitoring_config()

    async def start_monitoring(self):
        """启动监控服务"""
        # 启动系统状态监控
        self.monitoring_tasks["system"] = asyncio.create_task(
            self._system_status_monitor()
        )

        # 启动策略状态监控（多实例模式）
        self.monitoring_tasks["strategies"] = asyncio.create_task(
            self._multi_instance_strategy_monitor()
        )

        # 启动代理健康检查
        self.monitoring_tasks["proxies"] = asyncio.create_task(
            self._proxy_health_monitor()
        )

        # 启动API Gateway健康检查
        self.monitoring_tasks["gateway"] = asyncio.create_task(
            self._gateway_health_monitor()
        )

    async def _multi_instance_strategy_monitor(self):
        """多实例策略监控"""
        interval = self.config["strategy_status_interval"]
        cache_ttl = self.config["strategy_status_cache_ttl"]

        while True:
            try:
                # 通过API Gateway获取所有策略状态
                all_strategies_status = await self.api_gateway._get_all_strategies_status()

                # 处理每个策略的状态
                for strategy_id_str, strategy_data in all_strategies_status["strategies"].items():
                    strategy_id = int(strategy_id_str)

                    # 计算健康分数
                    health_score = await self._calculate_multi_instance_health_score(
                        strategy_data
                    )

                    # 添加时间戳和健康分数
                    enhanced_status = {
                        **strategy_data,
                        "health_score": health_score,
                        "last_update": time.time(),
                        "monitoring_mode": "multi_instance",
                        "strategy_id": strategy_id
                    }

                    # 更新Redis缓存
                    await self.redis_client.setex(
                        f"strategy:status:{strategy_id}",
                        cache_ttl,
                        json.dumps(enhanced_status)
                    )

                    # WebSocket实时推送
                    await self._broadcast_strategy_status(strategy_id, enhanced_status)

                # 更新总体统计
                await self._update_strategies_summary(all_strategies_status)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Multi-instance strategy monitoring error: {e}")
                await asyncio.sleep(interval)

    async def _gateway_health_monitor(self):
        """API Gateway健康监控"""
        while True:
            try:
                # 检查Gateway自身健康状态
                gateway_health = await self.api_gateway._gateway_health_check()

                # 更新Gateway健康状态
                await self.redis_client.setex(
                    "gateway:health",
                    60,  # 1分钟TTL
                    json.dumps(gateway_health)
                )

                # 检查路由配置是否最新
                await self._verify_routes_sync()

                # 如果Gateway不健康，发送告警
                if gateway_health.get("health_score", 0) < 80:
                    await self._send_gateway_health_alert(gateway_health)

                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"Gateway health monitoring error: {e}")
                await asyncio.sleep(60)

    async def _verify_routes_sync(self):
        """验证路由配置同步状态"""
        try:
            # 检查FreqTrade Manager和API Gateway的策略列表是否一致
            manager_strategies = set(self.freqtrade_manager.strategy_processes.keys())
            gateway_routes = set(int(k) for k in self.api_gateway.routes_config.keys())

            if manager_strategies != gateway_routes:
                logger.warning(f"Routes mismatch: Manager={manager_strategies}, Gateway={gateway_routes}")

                # 自动同步路由配置
                await self.freqtrade_manager._update_gateway_routes()
                await self.api_gateway._reload_routes_config()

        except Exception as e:
            logger.error(f"Routes sync verification failed: {e}")

    async def _calculate_multi_instance_health_score(self, strategy_data: dict) -> int:
        """计算多实例模式健康分数"""
        score = 100

        # 基础连接状态 (40分)
        status = strategy_data.get("status", "unknown")
        if status == "unreachable":
            score -= 40
        elif status == "error":
            score -= 30
        elif status != "healthy":
            score -= 20

        # 响应时间 (20分)
        if "response_time" in strategy_data:
            response_time = strategy_data["response_time"]
            if response_time > 5000:  # 5秒
                score -= 20
            elif response_time > 2000:  # 2秒
                score -= 10
            elif response_time > 1000:  # 1秒
                score -= 5

        # FreqTrade内部状态 (40分)
        if "data" in strategy_data and isinstance(strategy_data["data"], dict):
            freqtrade_data = strategy_data["data"]

            # 检查策略运行状态
            if "state" in freqtrade_data:
                if freqtrade_data["state"] != "running":
                    score -= 20

            # 检查最近处理时间
            if "last_process" in freqtrade_data:
                last_process = freqtrade_data["last_process"]
                time_diff = time.time() - last_process
                if time_diff > 300:  # 5分钟无处理
                    score -= 20

        return max(0, score)

    async def _update_strategies_summary(self, all_strategies_status: dict):
        """更新策略汇总统计"""
        strategies = all_strategies_status.get("strategies", {})

        summary = {
            "total_strategies": len(strategies),
            "healthy_strategies": len([s for s in strategies.values()
                                     if s.get("status") == "healthy"]),
            "error_strategies": len([s for s in strategies.values()
                                   if s.get("status") == "error"]),
            "unreachable_strategies": len([s for s in strategies.values()
                                         if s.get("status") == "unreachable"]),
            "gateway_status": all_strategies_status.get("gateway_status", "unknown"),
            "last_update": time.time()
        }

        # 更新Redis汇总
        await self.redis_client.setex(
            "strategies:summary",
            self.config["strategy_status_cache_ttl"],
            json.dumps(summary)
        )

        # 广播汇总更新
        await self._broadcast_strategies_summary(summary)

    async def _send_gateway_health_alert(self, health_data: dict):
        """发送Gateway健康告警"""
        alert_message = {
            "type": "gateway_unhealthy",
            "health_score": health_data.get("health_score", 0),
            "healthy_strategies": health_data.get("healthy_strategies", 0),
            "total_strategies": health_data.get("total_strategies", 0),
            "timestamp": time.time(),
            "priority": "P0",
            "architecture": "multi_instance"
        }

        # 发送到通知系统
        await self._send_system_alert(alert_message)

    async def get_comprehensive_status(self, strategy_id: int = None) -> dict:
        """获取策略的综合状态信息（多实例模式）"""
        try:
            if strategy_id is None:
                # 返回所有策略状态
                strategies_summary = await self.redis_client.get("strategies:summary")
                if strategies_summary:
                    return json.loads(strategies_summary)
                else:
                    return {"error": "No strategies summary available"}

            # 获取指定策略状态
            cached_status = await self.redis_client.get(f"strategy:status:{strategy_id}")
            if cached_status:
                status_data = json.loads(cached_status)
            else:
                # 实时获取状态
                gateway_status = await self.api_gateway._get_all_strategies_status()
                strategy_data = gateway_status["strategies"].get(str(strategy_id))
                if strategy_data:
                    status_data = strategy_data
                else:
                    return {"error": f"Strategy {strategy_id} not found"}

            # 获取Gateway健康状态
            gateway_health = await self.redis_client.get("gateway:health")
            if gateway_health:
                status_data["gateway_health"] = json.loads(gateway_health)

            return status_data

        except Exception as e:
            return {"error": str(e)}

    async def get_all_strategies_overview(self) -> dict:
        """获取所有策略概览（多实例模式）"""
        try:
            # 获取策略汇总
            strategies_summary = await self.redis_client.get("strategies:summary")
            if strategies_summary:
                summary_data = json.loads(strategies_summary)
            else:
                summary_data = {"error": "Summary data not available"}

            # 获取Gateway健康状态
            gateway_health = await self.redis_client.get("gateway:health")
            if gateway_health:
                gateway_data = json.loads(gateway_health)
            else:
                gateway_data = {"error": "Gateway health data not available"}

            # 获取所有策略的详细状态
            all_strategies = {}
            gateway_status = await self.api_gateway._get_all_strategies_status()

            for strategy_id_str, strategy_data in gateway_status.get("strategies", {}).items():
                strategy_id = int(strategy_id_str)

                # 从缓存获取增强状态
                cached_status = await self.redis_client.get(f"strategy:status:{strategy_id}")
                if cached_status:
                    all_strategies[strategy_id] = json.loads(cached_status)
                else:
                    all_strategies[strategy_id] = strategy_data

            return {
                "summary": summary_data,
                "gateway": gateway_data,
                "strategies": all_strategies,
                "architecture": "multi_instance",
                "monitoring_mode": "gateway_based"
            }

        except Exception as e:
            return {"error": str(e)}

    async def reload_config(self):
        """重新加载配置"""
        config_manager.reload_config("system")
        self.config = config_manager.get_monitoring_config()
        logger.info("Monitoring service config reloaded for multi-instance mode")
```
```
```
# backend/api/v1/signals.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

router = APIRouter()

class FreqTradeSignal(BaseModel):
    """FreqTrade信号数据模型"""
    strategy: str
    pair: str
    action: str  # buy, sell, hold
    current_rate: float
    profit: float
    open_date: str
    close_date: Optional[str]
    trade_id: Optional[int]

    # 自定义指标数据
    indicators: dict = {}
    metadata: dict = {}

@router.post("/webhook")
async def receive_freqtrade_signal(signal: FreqTradeSignal):
    """接收FreqTrade策略信号"""
    try:
        # 1. 解析信号数据
        processed_signal = await process_signal_data(signal)

        # 2. 计算信号强度 (基于策略自定义逻辑)
        signal_strength = await calculate_signal_strength(processed_signal)

        # 3. 存储到数据库
        await save_signal_to_database(processed_signal)

        # 4. 实时推送到WebSocket
        await broadcast_signal_update(processed_signal)

        # 5. 触发通知 (根据强度阈值)
        await trigger_notifications_if_needed(processed_signal)

        return {"status": "success", "signal_id": processed_signal["id"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal processing failed: {str(e)}")

async def calculate_signal_strength(signal_data: dict) -> dict:
    """计算信号强度 (策略输出数值 + UI配置阈值)"""
    strategy_name = signal_data["strategy_name"]

    # 从信号数据中获取策略输出的强度值
    raw_strength = signal_data.get("indicators", {}).get("signal_strength", 0)

    # 获取该策略的阈值配置
    thresholds = await get_strategy_thresholds(strategy_name)

    # 计算强度等级和优先级
    if raw_strength >= thresholds["strong_threshold"]:
        strength_level = "strong"
        priority = "P0"
    elif raw_strength >= thresholds["medium_threshold"]:
        strength_level = "medium"
        priority = "P1"
    elif raw_strength >= thresholds["weak_threshold"]:
        strength_level = "weak"
        priority = "P2"
    else:
        strength_level = "ignore"
        priority = "IGNORE"

    return {
        "strength_raw": raw_strength,
        "strength_level": strength_level,
        "priority": priority
    }
```

---

## 2. 系统监控实现

### 2.1 监控服务架构

```python
# backend/services/monitoring_service.py
import asyncio
import time
from typing import Dict
import psutil
import redis.asyncio as redis

class SystemMonitoringService:
    """系统监控服务"""

    def __init__(self):
        self.redis_client = None
        self.freqtrade_manager = None
        self.monitoring_tasks = {}

    async def start_monitoring(self):
        """启动监控服务"""
        # 启动系统状态监控 (30秒)
        self.monitoring_tasks["system"] = asyncio.create_task(
            self._system_status_monitor()
        )

        # 启动策略状态监控 (30秒)
        self.monitoring_tasks["strategies"] = asyncio.create_task(
            self._strategy_status_monitor()
        )

        # 启动代理健康检查 (1小时)
        self.monitoring_tasks["proxies"] = asyncio.create_task(
            self._proxy_health_monitor()
        )

    async def _system_status_monitor(self):
        """系统状态监控 - 30秒间隔"""
        while True:
            try:
                system_status = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent,
                    "network_io": psutil.net_io_counters()._asdict(),
                    "uptime_seconds": time.time() - psutil.boot_time()
                }

                # 更新Redis缓存 (30秒TTL)
                await self.redis_client.setex(
                    "system:status",
                    30,
                    json.dumps(system_status)
                )

                # WebSocket广播
                await self._broadcast_system_status(system_status)

                await asyncio.sleep(30)  # 30秒间隔

            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(30)

    async def _strategy_status_monitor(self):
        """策略状态监控 - 30秒间隔"""
        while True:
            try:
                # 获取所有活跃策略
                active_strategies = await get_active_strategies()

                for strategy in active_strategies:
                    # 获取策略运行状态
                    status = await self.freqtrade_manager.get_strategy_status(
                        strategy["id"]
                    )

                    # 计算健康分数
                    health_score = await self._calculate_health_score(strategy, status)

                    # 更新Redis缓存 (30秒TTL)
                    await self.redis_client.setex(
                        f"strategy:status:{strategy['id']}",
                        30,
                        json.dumps({**status, "health_score": health_score})
                    )

                await asyncio.sleep(30)  # 30秒间隔

            except Exception as e:
                logger.error(f"Strategy monitoring error: {e}")
                await asyncio.sleep(30)
```

### 2.2 数据备份服务

```python
# backend/services/backup_service.py
import asyncio
import subprocess
from datetime import datetime, timedelta

class BackupService:
    """数据备份服务 - 永久保存策略"""

    def __init__(self):
        self.backup_retention_days = 90  # 备份文件保留90天

    async def daily_backup(self):
        """每日自动备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # PostgreSQL备份
            pg_backup_file = f"/backup/postgresql_{timestamp}.sql.gz"
            await self._backup_postgresql(pg_backup_file)

            # Redis备份
            redis_backup_file = f"/backup/redis_{timestamp}.rdb"
            await self._backup_redis(redis_backup_file)

            # 策略代码备份
            strategies_backup_file = f"/backup/strategies_{timestamp}.tar.gz"
            await self._backup_strategies(strategies_backup_file)

            # 清理过期备份
            await self._cleanup_old_backups()

            logger.info(f"Daily backup completed: {timestamp}")

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            await self._send_backup_alert(str(e))

    async def _backup_postgresql(self, backup_file: str):
        """PostgreSQL备份 - 永久保存数据"""
        cmd = [
            "pg_dump",
            "-h", "db",
            "-U", "btc_watcher",
            "-d", "btc_watcher",
            "--no-password"
        ]

        # 压缩备份
        with open(backup_file, 'wb') as f:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            gzip_process = subprocess.Popen(
                ["gzip"],
                stdin=process.stdout,
                stdout=f,
                stderr=subprocess.PIPE
            )

            process.stdout.close()
            gzip_process.communicate()

    async def _cleanup_old_backups(self):
        """清理过期备份文件"""
        cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)

        cmd = [
            "find", "/backup",
            "-name", "*.gz",
            "-o", "-name", "*.rdb",
            "-o", "-name", "*.tar.gz",
            "-mtime", f"+{self.backup_retention_days}",
            "-delete"
        ]

        subprocess.run(cmd)
```

---

## 3. Docker部署配置

### 1.7 更新的Docker部署配置

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    postgresql-client \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 安装FreqTrade 2025.8
RUN pip install freqtrade==2025.8

# 复制并安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p /app/freqtrade_data \
    /app/freqtrade_configs \
    /app/user_data/strategies \
    /app/logs \
    /app/gateway_config \
    /backup

# 设置环境变量
ENV PYTHONPATH=/app
ENV FREQTRADE_VERSION=2025.8
ENV FREQTRADE_GATEWAY_PORT=8080
ENV FREQTRADE_BASE_PORT=8081
ENV FREQTRADE_MAX_PORT=9080
ENV MAX_CONCURRENT_STRATEGIES=999

# 创建启动脚本
COPY docker/start-services.sh /start-services.sh
RUN chmod +x /start-services.sh

# 启动命令
CMD ["/start-services.sh"]
```

```bash
#!/bin/bash
# docker/start-services.sh - 多服务启动脚本

set -e

echo "Starting BTC Watcher Multi-Instance Services..."

# 1. 启动主API服务
echo "Starting Main API Service..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# 2. 启动API Gateway
echo "Starting FreqTrade API Gateway..."
python -c "
import asyncio
from core.api_gateway import FreqTradeAPIGateway

async def start_gateway():
    gateway = FreqTradeAPIGateway(gateway_port=8080)
    await gateway.start_gateway()

asyncio.run(start_gateway())
" &
GATEWAY_PID=$!

# 3. 启动监控服务
echo "Starting Monitoring Service..."
python -m services.monitoring_service &
MONITOR_PID=$!

# 4. 启动通知服务
echo "Starting Notification Service..."
python -m services.notification_service &
NOTIFICATION_PID=$!

# 等待所有服务
wait $API_PID $GATEWAY_PID $MONITOR_PID $NOTIFICATION_PID
```

```yaml
# docker-compose.yml - 反向代理多实例模式
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: btc-watcher-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - web
      - api
    networks:
      - btc-watcher-network

  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: btc-watcher-web
    environment:
      - NODE_ENV=production
      - VUE_APP_API_URL=http://api:8000
      - VUE_APP_GATEWAY_URL=http://api:8080
      - VUE_APP_WS_URL=ws://api:8000/ws
    volumes:
      - ./frontend/dist:/app/dist
    networks:
      - btc-watcher-network

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: btc-watcher-api
    environment:
      - DATABASE_URL=postgresql://btc_watcher:password@db:5432/btc_watcher
      - REDIS_URL=redis://redis:6379/0
      - FREQTRADE_VERSION=2025.8
      - FREQTRADE_GATEWAY_PORT=8080
      - FREQTRADE_BASE_PORT=8081
      - FREQTRADE_MAX_PORT=9080
      - ARCHITECTURE_MODE=multi_instance
      - MAX_CONCURRENT_STRATEGIES=999
    ports:
      - "8000:8000"
      - "8080:8080"  # FreqTrade API Gateway统一端口
      - "8081-9080:8081-9080"  # FreqTrade实例端口范围 (999个端口)
    volumes:
      - ./backend:/app
      - ./user_data:/app/user_data
      - ./freqtrade_configs:/app/freqtrade_configs
      - ./logs:/app/logs
      - ./backup:/backup
      - ./gateway_config:/app/gateway_config
    depends_on:
      - db
      - redis
    networks:
      - btc-watcher-network

  notification:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: btc-watcher-notification
    environment:
      - DATABASE_URL=postgresql://btc_watcher:password@db:5432/btc_watcher
      - REDIS_URL=redis://redis:6379/0
      - ARCHITECTURE_MODE=multi_instance
    command: python -m services.notification_service
    depends_on:
      - db
      - redis
    networks:
      - btc-watcher-network

  db:
    image: postgres:15-alpine
    container_name: btc-watcher-db
    environment:
      - POSTGRES_DB=btc_watcher
      - POSTGRES_USER=btc_watcher
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - btc-watcher-network

  redis:
    image: redis:7-alpine
    container_name: btc-watcher-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - btc-watcher-network

volumes:
  postgres_data:
  redis_data:

networks:
  btc-watcher-network:
    driver: bridge
```

```nginx
# nginx/nginx.conf - 反向代理配置
upstream btc_watcher_api {
    server api:8000;
}

upstream freqtrade_gateway {
    server api:8080;
}

server {
    listen 80;
    server_name localhost;

    # 主API代理
    location /api/ {
        proxy_pass http://btc_watcher_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # FreqTrade Gateway代理
    location /freqtrade/ {
        proxy_pass http://freqtrade_gateway/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # FreqTrade API特殊配置
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    # WebSocket代理
    location /ws {
        proxy_pass http://btc_watcher_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # 静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }
}
```

### 1.8 更新的requirements.txt

```txt
# backend/requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
asyncpg==0.29.0
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
websockets==12.0
aiofiles==23.2.1
psutil==5.9.6
aiohttp==3.9.1
# FreqTrade dependencies will be installed via pip install freqtrade==2025.8
```

### 1.9 系统集成和启动流程

```python
# backend/main.py - 主应用启动文件
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from core.freqtrade_manager import FreqTradeGatewayManager
from core.api_gateway import FreqTradeAPIGateway
from services.monitoring_service import EnhancedMonitoringService
from core.config_manager import config_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="BTC Watcher API",
    description="Cryptocurrency Signal Monitoring System",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
freqtrade_manager: FreqTradeGatewayManager = None
api_gateway: FreqTradeAPIGateway = None
monitoring_service: EnhancedMonitoringService = None

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global freqtrade_manager, api_gateway, monitoring_service

    logger.info("Starting BTC Watcher Multi-Instance System...")

    try:
        # 1. 初始化FreqTrade管理器
        freqtrade_manager = FreqTradeGatewayManager()
        logger.info("FreqTrade Gateway Manager initialized")

        # 2. 初始化API Gateway
        api_gateway = FreqTradeAPIGateway(gateway_port=8080)
        logger.info("API Gateway initialized")

        # 3. 初始化监控服务
        monitoring_service = EnhancedMonitoringService()
        monitoring_service.freqtrade_manager = freqtrade_manager
        monitoring_service.api_gateway = api_gateway

        # 4. 启动监控服务
        await monitoring_service.start_monitoring()
        logger.info("Monitoring service started")

        # 5. 连接Redis
        import redis.asyncio as redis
        redis_client = redis.from_url("redis://redis:6379/0")
        monitoring_service.redis_client = redis_client

        logger.info("BTC Watcher system startup completed")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down BTC Watcher system...")

    try:
        # 停止所有策略
        if freqtrade_manager:
            await freqtrade_manager.stop_all_strategies()

        # 停止监控服务
        if monitoring_service:
            for task_name, task in monitoring_service.monitoring_tasks.items():
                task.cancel()
                logger.info(f"Cancelled {task_name} monitoring task")

        logger.info("BTC Watcher system shutdown completed")

    except Exception as e:
        logger.error(f"Shutdown error: {e}")

# 依赖注入函数
async def get_freqtrade_manager():
    return freqtrade_manager

async def get_api_gateway():
    return api_gateway

async def get_monitoring_service():
    return monitoring_service

# 注册API路由
from api.v1 import auth, strategies, signals, notifications, system

app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

# 健康检查端点
@app.get("/health")
async def health_check():
    """系统健康检查"""
    try:
        health_status = {
            "status": "healthy",
            "architecture": "multi_instance",
            "services": {
                "freqtrade_manager": freqtrade_manager is not None,
                "api_gateway": api_gateway is not None,
                "monitoring_service": monitoring_service is not None
            }
        }

        # 检查API Gateway健康状态
        if api_gateway:
            gateway_health = await api_gateway._gateway_health_check()
            health_status["gateway"] = gateway_health

        return health_status

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "architecture": "multi_instance"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
```

---

## 反向代理统一端口架构优势总结

### FreqTrade多实例管理模式的技术优势

**1. 架构扩展性**
- **并发执行**: 多个策略同时运行，满足严谨量化信号系统需求
- **进程隔离**: 每个策略独立进程，单个策略故障不影响其他策略
- **端口管理**: 内部多端口+外部统一端口，兼顾隔离性和易用性
- **动态扩展**: 支持动态添加/删除策略实例，无需重启系统

**2. 运维优势**
- **统一入口**: 8080端口提供统一API访问，简化客户端配置
- **健康监控**: API Gateway提供所有策略的统一健康检查
- **路由管理**: 自动路由配置同步，确保管理器和网关一致性
- **故障隔离**: 单个策略故障通过Gateway快速识别和隔离

**3. 技术特性**
- **负载均衡**: Gateway支持请求路由和负载分配
- **实时监控**: 多实例状态实时汇总和推送
- **配置同步**: 自动检测和同步路由配置变更
- **错误恢复**: Gateway自动检测上游服务状态并重试

### 与单实例方案的对比

| 特性 | 多实例反向代理模式 ✓ | 单实例模式 |
|------|---------------------|------------|
| 策略并发 | 多策略并行执行 | 单策略顺序执行 |
| 故障隔离 | 完全隔离 | 单点故障 |
| 扩展性 | 动态扩展 | 受限扩展 |
| 资源利用 | 充分利用多核 | 单核限制 |
| 监控复杂度 | Gateway统一管理 | 相对简单 |
| 系统稳定性 | 高（故障隔离） | 中（单点风险） |

### 适用场景确认

**多实例反向代理模式适合**：
- ✅ 严谨的量化信号系统（满足用户需求）
- ✅ 3-5个策略同时运行（符合用户预期）
- ✅ 高可用性要求（单策略故障不影响系统）
- ✅ 资深开发者使用（具备运维能力）

### 实现细节确认

**核心确认事项**：
1. ✅ FreqTrade 2025.8版本，代码集成模式
2. ✅ 反向代理架构，内部多端口(8081+)+外部统一端口(8080)
3. ✅ 每个策略独立FreqTrade进程，支持并发执行
4. ✅ API Gateway提供统一路由和健康检查
5. ✅ 监控服务适配多实例架构，实时状态汇总
6. ✅ Docker配置支持端口范围映射和多服务启动

**技术实现特点**：
- FreqTradeGatewayManager负责多实例生命周期管理
- FreqTradeAPIGateway提供统一端口访问和路由转发
- EnhancedMonitoringService适配多实例状态监控
- Docker支持端口范围映射(8081-9080)，共999个端口
- 端口池自动管理，支持动态分配和释放
- Nginx提供外部访问的反向代理配置

### 超大规模扩展能力

**999个并发策略支持**：
- **端口范围**: 8081-9080 (999个独立端口)
- **端口池管理**: 自动分配、释放、复用机制
- **资源隔离**: 每个策略独立进程和端口
- **容量监控**: 实时追踪端口使用率和可用槽位
- **弹性扩展**: 支持运行时动态增减策略数量

**端口池管理优势**：
```python
# 智能端口分配
- 优先分配策略ID对应的端口 (base_port + strategy_id)
- 端口冲突时自动分配最小可用端口
- 策略停止时自动释放端口回池

# 容量管理
- 实时监控端口使用率
- 防止超过最大并发限制 (999个)
- 提供容量信息API供前端展示
```

**适用场景扩展**：
- ✅ **个人使用**: 3-5个策略 (< 1% 容量)
- ✅ **小团队**: 10-20个策略 (< 2% 容量)
- ✅ **专业团队**: 50-100个策略 (< 10% 容量)
- ✅ **机构级别**: 100-999个策略 (< 100% 容量)

**性能预估**：
```
策略数量    内存占用 (估算)    CPU使用 (估算)
--------    ---------------    --------------
5个         ~2GB              ~10%
20个        ~8GB              ~30%
50个        ~20GB             ~60%
100个       ~40GB             ~80%
999个       ~400GB            接近满载
```

**建议配置**：
- **个人用户 (3-5策略)**: 4核CPU + 8GB内存
- **小团队 (10-20策略)**: 8核CPU + 16GB内存
- **专业团队 (50-100策略)**: 16核CPU + 64GB内存
- **机构级别 (100+策略)**: 32核CPU + 128GB+ 内存

---

## 5. 系统配置管理

### 5.1 配置文件结构

```yaml
# config/system.yml - 系统核心配置
system:
  monitoring:
    # 监控频率设置
    system_status_interval: 30        # 系统状态监控间隔(秒)
    strategy_status_interval: 30      # 策略状态监控间隔(秒)
    proxy_health_interval: 3600       # 代理健康检查间隔(秒)

    # 缓存TTL设置
    system_status_cache_ttl: 30       # 系统状态缓存时间(秒)
    strategy_status_cache_ttl: 30     # 策略状态缓存时间(秒)
    chart_data_cache_ttl: 600         # 图表数据缓存时间(秒)

  performance:
    # 数据库连接池
    db_pool_min_size: 5
    db_pool_max_size: 20
    db_command_timeout: 60

    # Redis配置
    redis_max_connections: 20
    redis_retry_attempts: 3

  security:
    # JWT设置
    jwt_secret_key: "your-secret-key"
    jwt_expire_hours: 24
    jwt_algorithm: "HS256"

    # 登录安全
    max_login_attempts: 5
    lockout_duration_minutes: 30

    # 密码策略
    min_password_length: 8
    require_special_chars: true

  backup:
    # 备份策略
    auto_backup_enabled: true
    backup_interval_hours: 24
    backup_retention_days: 90

    # 备份路径
    backup_directory: "/backup"

  freqtrade:
    # FreqTrade集成设置
    version: "2025.8"
    config_directory: "/app/freqtrade_configs"
    strategies_directory: "/app/user_data/strategies"
    logs_directory: "/app/logs"
    data_directory: "/app/freqtrade_data"

    # 进程管理
    startup_timeout: 60
    shutdown_timeout: 30
    health_check_interval: 30
```

```yaml
# config/notifications.yml - 通知配置
notifications:
  # 通知频率控制
  rate_limiting:
    same_pair_interval: 300           # 同币种信号间隔(秒)
    global_max_per_minute: 5          # 全局每分钟最大通知数
    batch_interval: 300               # 批量通知间隔(秒)

  # 优先级设置
  priorities:
    P0:
      name: "立即通知"
      delay_seconds: 0
      channels: ["sms", "feishu", "wechat"]
    P1:
      name: "1分钟内通知"
      delay_seconds: 60
      channels: ["feishu", "wechat", "email"]
    P2:
      name: "批量通知"
      delay_seconds: 300
      channels: ["email"]

  # 时间段控制
  time_slots:
    work_hours:
      start_time: "09:00"
      end_time: "18:00"
      enabled_priorities: ["P0", "P1", "P2"]
      enabled_channels: ["sms", "feishu", "wechat", "email"]

    rest_hours:
      start_time: "18:00"
      end_time: "09:00"
      enabled_priorities: ["P0"]
      enabled_channels: ["sms"]

  # 消息模板
  templates:
    signal_template: "simple"        # simple, detailed, custom
    include_indicators: true
    include_chart_link: true
    include_chart_screenshot: false
```

```yaml
# config/proxy.yml - 代理配置
proxy:
  # 健康检查标准
  health_check:
    success_rate_threshold: 90        # 成功率阈值(%)
    max_latency_ms: 500              # 最大延迟(毫秒)
    max_consecutive_failures: 3      # 最大连续失败次数
    test_url: "https://api.binance.com/api/v3/ping"

  # 故障切换
  failover:
    enable_direct_connection: true    # 启用直连模式
    auto_recovery_check_interval: 600 # 自动恢复检查间隔(秒)
    recovery_success_count: 3        # 恢复所需连续成功次数

  # 性能监控
  monitoring:
    metrics_retention_hours: 24      # 性能指标保留时间
    alert_on_degradation: true       # 性能下降时告警
    latency_spike_threshold: 200     # 延迟激增阈值(%)
```

### 5.2 配置管理器实现

```python
# backend/core/config_manager.py
import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """统一配置管理器"""

    def __init__(self, config_dir: str = "/app/config"):
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, Dict] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        """加载所有配置文件"""
        config_files = [
            "system.yml",
            "notifications.yml",
            "proxy.yml"
        ]

        for config_file in config_files:
            config_path = self.config_dir / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_name = config_file.replace('.yml', '')
                        self.configs[config_name] = yaml.safe_load(f)
                        logger.info(f"Loaded config: {config_file}")
                except Exception as e:
                    logger.error(f"Failed to load config {config_file}: {e}")
                    # 使用默认配置
                    self.configs[config_name] = self._get_default_config(config_name)
            else:
                logger.warning(f"Config file not found: {config_file}, using defaults")
                config_name = config_file.replace('.yml', '')
                self.configs[config_name] = self._get_default_config(config_name)

    def get(self, config_key: str, default: Any = None) -> Any:
        """获取配置值

        Args:
            config_key: 配置键，格式: "config_file.section.key"
            default: 默认值

        Returns:
            配置值
        """
        try:
            keys = config_key.split('.')
            config_name = keys[0]

            if config_name not in self.configs:
                return default

            value = self.configs[config_name]
            for key in keys[1:]:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default

            return value
        except Exception:
            return default

    def get_monitoring_config(self) -> Dict[str, int]:
        """获取监控配置"""
        return {
            "system_status_interval": self.get("system.monitoring.system_status_interval", 30),
            "strategy_status_interval": self.get("system.monitoring.strategy_status_interval", 30),
            "proxy_health_interval": self.get("system.monitoring.proxy_health_interval", 3600),
            "system_status_cache_ttl": self.get("system.monitoring.system_status_cache_ttl", 30),
            "strategy_status_cache_ttl": self.get("system.monitoring.strategy_status_cache_ttl", 30),
            "chart_data_cache_ttl": self.get("system.monitoring.chart_data_cache_ttl", 600)
        }

    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return {
            "min_size": self.get("system.performance.db_pool_min_size", 5),
            "max_size": self.get("system.performance.db_pool_max_size", 20),
            "command_timeout": self.get("system.performance.db_command_timeout", 60)
        }

    def get_notification_config(self) -> Dict[str, Any]:
        """获取通知配置"""
        return {
            "rate_limiting": self.get("notifications.rate_limiting", {}),
            "priorities": self.get("notifications.priorities", {}),
            "time_slots": self.get("notifications.time_slots", {}),
            "templates": self.get("notifications.templates", {})
        }

    def get_proxy_config(self) -> Dict[str, Any]:
        """获取代理配置"""
        return {
            "health_check": self.get("proxy.health_check", {}),
            "failover": self.get("proxy.failover", {}),
            "monitoring": self.get("proxy.monitoring", {})
        }

    def reload_config(self, config_name: Optional[str] = None):
        """重新加载配置"""
        if config_name:
            # 重新加载指定配置文件
            config_path = self.config_dir / f"{config_name}.yml"
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self.configs[config_name] = yaml.safe_load(f)
                        logger.info(f"Reloaded config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to reload config {config_name}: {e}")
        else:
            # 重新加载所有配置
            self._load_all_configs()

    def _get_default_config(self, config_name: str) -> Dict:
        """获取默认配置"""
        defaults = {
            "system": {
                "monitoring": {
                    "system_status_interval": 30,
                    "strategy_status_interval": 30,
                    "proxy_health_interval": 3600,
                    "system_status_cache_ttl": 30,
                    "strategy_status_cache_ttl": 30,
                    "chart_data_cache_ttl": 600
                },
                "performance": {
                    "db_pool_min_size": 5,
                    "db_pool_max_size": 20,
                    "db_command_timeout": 60
                },
                "freqtrade": {
                    "version": "2025.8",
                    "startup_timeout": 60,
                    "shutdown_timeout": 30,
                    "health_check_interval": 30
                }
            },
            "notifications": {
                "rate_limiting": {
                    "same_pair_interval": 300,
                    "global_max_per_minute": 5,
                    "batch_interval": 300
                }
            },
            "proxy": {
                "health_check": {
                    "success_rate_threshold": 90,
                    "max_latency_ms": 500,
                    "max_consecutive_failures": 3
                }
            }
        }

        return defaults.get(config_name, {})

# 全局配置管理器实例
config_manager = ConfigManager()
```

### 5.3 集成配置管理到监控服务

```python
# 更新 backend/services/monitoring_service.py
from core.config_manager import config_manager

class SystemMonitoringService:
    def __init__(self):
        self.redis_client = None
        self.freqtrade_manager = None
        self.monitoring_tasks = {}
        self.config = config_manager.get_monitoring_config()

    async def start_monitoring(self):
        """启动监控服务 - 使用配置文件参数"""
        # 启动系统状态监控
        self.monitoring_tasks["system"] = asyncio.create_task(
            self._system_status_monitor()
        )

        # 启动策略状态监控
        self.monitoring_tasks["strategies"] = asyncio.create_task(
            self._strategy_status_monitor()
        )

        # 启动代理健康检查
        self.monitoring_tasks["proxies"] = asyncio.create_task(
            self._proxy_health_monitor()
        )

    async def _system_status_monitor(self):
        """系统状态监控 - 使用配置的间隔时间"""
        interval = self.config["system_status_interval"]
        cache_ttl = self.config["system_status_cache_ttl"]

        while True:
            try:
                system_status = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent,
                    "network_io": psutil.net_io_counters()._asdict(),
                    "uptime_seconds": time.time() - psutil.boot_time()
                }

                # 更新Redis缓存 (使用配置的TTL)
                await self.redis_client.setex(
                    "system:status",
                    cache_ttl,
                    json.dumps(system_status)
                )

                # WebSocket广播
                await self._broadcast_system_status(system_status)

                await asyncio.sleep(interval)  # 使用配置的间隔

            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(interval)

    async def _strategy_status_monitor(self):
        """策略状态监控 - 使用配置的间隔时间"""
        interval = self.config["strategy_status_interval"]
        cache_ttl = self.config["strategy_status_cache_ttl"]

        while True:
            try:
                # 获取所有活跃策略
                active_strategies = await get_active_strategies()

                for strategy in active_strategies:
                    # 获取策略运行状态
                    status = await self.freqtrade_manager.get_strategy_status(
                        strategy["id"]
                    )

                    # 计算健康分数
                    health_score = await self._calculate_health_score(strategy, status)

                    # 更新Redis缓存
                    await self.redis_client.setex(
                        f"strategy:status:{strategy['id']}",
                        cache_ttl,
                        json.dumps({**status, "health_score": health_score})
                    )

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Strategy monitoring error: {e}")
                await asyncio.sleep(interval)

    async def reload_config(self):
        """重新加载配置"""
        config_manager.reload_config("system")
        self.config = config_manager.get_monitoring_config()
        logger.info("Monitoring service config reloaded")
```

### 5.4 配置管理API

```python
# backend/api/v1/system.py
@router.get("/config/{config_name}")
async def get_config(config_name: str):
    """获取配置信息"""
    if config_name == "monitoring":
        return config_manager.get_monitoring_config()
    elif config_name == "notifications":
        return config_manager.get_notification_config()
    elif config_name == "proxy":
        return config_manager.get_proxy_config()
    else:
        raise HTTPException(status_code=404, detail="Config not found")

@router.post("/config/reload")
async def reload_config(config_name: Optional[str] = None):
    """重新加载配置"""
    try:
        config_manager.reload_config(config_name)

        # 通知相关服务重新加载配置
        if config_name in ["system", None]:
            await monitoring_service.reload_config()

        return {"status": "success", "message": "Config reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 4.1 策略管理API增强

```python
# backend/api/v1/strategies.py
from fastapi import APIRouter, HTTPException, Depends
from core.freqtrade_manager import FreqTradeIntegrationManager

router = APIRouter()

@router.post("/strategies")
async def create_strategy(
    strategy_data: StrategyCreateModel,
    ft_manager: FreqTradeIntegrationManager = Depends()
):
    """创建策略 - 支持FreqTrade代码集成"""
    try:
        # 1. 验证策略配置
        validated_config = await validate_strategy_config(strategy_data)

        # 2. 保存到数据库
        strategy_id = await save_strategy_to_db(validated_config)

        # 3. 如果需要立即启动
        if strategy_data.auto_start:
            await ft_manager.create_strategy({
                **validated_config,
                "id": strategy_id
            })

        return {"strategy_id": strategy_id, "status": "created"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/strategies/{strategy_id}/start")
async def start_strategy(
    strategy_id: int,
    ft_manager: FreqTradeIntegrationManager = Depends()
):
    """启动策略"""
    try:
        # 获取策略配置
        strategy_config = await get_strategy_config(strategy_id)

        # 启动FreqTrade实例
        await ft_manager.create_strategy(strategy_config)

        # 更新数据库状态
        await update_strategy_status(strategy_id, "running")

        return {"status": "started", "strategy_id": strategy_id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    ft_manager: FreqTradeIntegrationManager = Depends()
):
    """删除策略"""
    try:
        # 1. 停止FreqTrade实例
        await ft_manager.stop_strategy(strategy_id)

        # 2. 删除配置文件
        await cleanup_strategy_files(strategy_id)

        # 3. 从数据库删除 (保留信号历史数据)
        await soft_delete_strategy(strategy_id)

        return {"status": "deleted", "strategy_id": strategy_id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 4.2 版本管理API

```python
# backend/api/v1/freqtrade.py
@router.post("/freqtrade/upgrade")
async def upgrade_freqtrade(
    upgrade_data: FreqTradeUpgradeModel,
    ft_manager: FreqTradeIntegrationManager = Depends()
):
    """手动升级FreqTrade版本"""
    try:
        # 1. 停止所有策略
        await ft_manager.stop_all_strategies()

        # 2. 备份当前版本
        backup_id = await backup_current_version()

        # 3. 执行升级
        upgrade_result = await execute_freqtrade_upgrade(
            upgrade_data.target_version
        )

        # 4. 验证升级结果
        if upgrade_result["success"]:
            # 重启所有策略
            await ft_manager.restart_all_strategies()
            return {"status": "success", "backup_id": backup_id}
        else:
            # 回滚到备份版本
            await rollback_to_backup(backup_id)
            raise HTTPException(
                status_code=500,
                detail=f"Upgrade failed: {upgrade_result['error']}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 6. 系统容量监控API (999策略扩展)

### 6.1 容量监控API端点

```python
# backend/api/v1/system.py - 容量监控相关API

@router.get("/capacity")
async def get_system_capacity(
    ft_manager: FreqTradeGatewayManager = Depends()
):
    """获取系统容量信息

    返回示例:
    {
        "max_strategies": 999,
        "running_strategies": 5,
        "available_slots": 994,
        "utilization_percent": 0.50,
        "port_range": "8081-9080",
        "can_start_more": true,
        "architecture": "multi_instance_reverse_proxy"
    }
    """
    try:
        capacity_info = ft_manager.get_capacity_info()
        return capacity_info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get capacity info: {str(e)}"
        )


@router.get("/port-pool")
async def get_port_pool_status(
    ft_manager: FreqTradeGatewayManager = Depends()
):
    """获取端口池状态

    返回示例:
    {
        "total_ports": 999,
        "available_ports": 994,
        "allocated_ports": 5,
        "running_strategies": 5,
        "port_range": "8081-9080",
        "max_concurrent": 999
    }
    """
    try:
        port_pool_status = ft_manager.get_port_pool_status()
        return port_pool_status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get port pool status: {str(e)}"
        )


@router.get("/capacity/detailed")
async def get_detailed_capacity(
    ft_manager: FreqTradeGatewayManager = Depends(),
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """获取详细的系统容量和健康信息

    返回示例:
    {
        "capacity": {
            "max_strategies": 999,
            "running_strategies": 5,
            "available_slots": 994,
            "utilization_percent": 0.50,
            "port_range": "8081-9080",
            "can_start_more": true,
            "architecture": "multi_instance_reverse_proxy"
        },
        "port_pool": {
            "total_ports": 999,
            "available_ports": 994,
            "allocated_ports": 5,
            "running_strategies": 5,
            "port_range": "8081-9080",
            "max_concurrent": 999
        },
        "gateway_health": {
            "status": "healthy",
            "health_score": 100,
            "healthy_strategies": 5,
            "total_strategies": 5,
            "gateway_port": 8080,
            "routes_loaded": 5
        },
        "recommendations": [
            {
                "level": "info",
                "message": "系统容量充足 (0.50%)，大量可用槽位",
                "action": "normal_operation"
            },
            {
                "level": "info",
                "message": "当前配置建议: 4核CPU + 8GB内存 (个人使用级别)",
                "action": "hardware_recommendation"
            }
        ],
        "timestamp": 1234567890.123
    }
    """
    try:
        # 获取容量信息
        capacity_info = ft_manager.get_capacity_info()

        # 获取端口池状态
        port_pool_status = ft_manager.get_port_pool_status()

        # 获取Gateway健康状态
        gateway_health = await api_gateway._gateway_health_check()

        # 生成容量建议
        recommendations = _generate_capacity_recommendations(capacity_info)

        return {
            "capacity": capacity_info,
            "port_pool": port_pool_status,
            "gateway_health": gateway_health,
            "recommendations": recommendations,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detailed capacity: {str(e)}"
        )


@router.get("/capacity/utilization-trend")
async def get_capacity_utilization_trend(
    hours: int = 24,
    ft_manager: FreqTradeGatewayManager = Depends()
):
    """获取容量使用率趋势（过去N小时）

    参数:
        hours: 查询的小时数，默认24小时

    返回示例:
    {
        "period_hours": 24,
        "current_utilization": 0.50,
        "peak_utilization": 2.5,
        "average_utilization": 1.2,
        "trend": "stable",
        "data_points": [
            {"timestamp": 1234567890, "utilization": 0.5},
            {"timestamp": 1234567920, "utilization": 0.6},
            ...
        ]
    }
    """
    try:
        # 从Redis或数据库获取历史容量数据
        trend_data = await _get_capacity_trend_from_cache(hours)

        current_capacity = ft_manager.get_capacity_info()

        return {
            "period_hours": hours,
            "current_utilization": current_capacity["utilization_percent"],
            "peak_utilization": trend_data.get("peak", 0),
            "average_utilization": trend_data.get("average", 0),
            "trend": trend_data.get("trend", "stable"),
            "data_points": trend_data.get("data_points", [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get utilization trend: {str(e)}"
        )


@router.post("/capacity/alert-threshold")
async def set_capacity_alert_threshold(
    threshold_percent: float,
    ft_manager: FreqTradeGatewayManager = Depends()
):
    """设置容量告警阈值

    参数:
        threshold_percent: 告警阈值百分比 (0-100)

    返回示例:
    {
        "status": "success",
        "threshold": 80.0,
        "message": "Capacity alert threshold set to 80.0%"
    }
    """
    try:
        if threshold_percent < 0 or threshold_percent > 100:
            raise HTTPException(
                status_code=400,
                detail="Threshold must be between 0 and 100"
            )

        # 保存阈值到配置或数据库
        await _save_capacity_alert_threshold(threshold_percent)

        return {
            "status": "success",
            "threshold": threshold_percent,
            "message": f"Capacity alert threshold set to {threshold_percent}%"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set alert threshold: {str(e)}"
        )


@router.get("/statistics")
async def get_system_statistics(
    ft_manager: FreqTradeGatewayManager = Depends(),
    api_gateway: FreqTradeAPIGateway = Depends()
):
    """获取系统统计信息

    返回示例:
    {
        "total_strategies": 5,
        "max_strategies": 999,
        "healthy_strategies": 4,
        "capacity_utilization": 0.50,
        "port_range": "8081-9080",
        "uptime_seconds": 86400,
        "architecture_mode": "multi_instance_reverse_proxy",
        "can_start_more": true
    }
    """
    try:
        # 获取容量信息
        capacity_info = ft_manager.get_capacity_info()

        # 获取Gateway统计
        gateway_health = await api_gateway._gateway_health_check()

        # 获取系统运行时间
        import psutil
        import time
        uptime_seconds = time.time() - psutil.boot_time()

        return {
            "total_strategies": capacity_info["running_strategies"],
            "max_strategies": capacity_info["max_strategies"],
            "healthy_strategies": gateway_health.get("healthy_strategies", 0),
            "capacity_utilization": capacity_info["utilization_percent"],
            "port_range": capacity_info["port_range"],
            "uptime_seconds": uptime_seconds,
            "architecture_mode": "multi_instance_reverse_proxy",
            "can_start_more": capacity_info["can_start_more"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )
```

### 6.2 容量建议生成逻辑

```python
def _generate_capacity_recommendations(capacity_info: dict) -> list:
    """生成容量建议

    根据当前容量使用率和运行策略数量，生成针对性的建议
    """
    recommendations = []
    utilization = capacity_info["utilization_percent"]
    running = capacity_info["running_strategies"]
    max_strategies = capacity_info["max_strategies"]

    # 容量使用率建议
    if utilization > 90:
        recommendations.append({
            "level": "critical",
            "message": f"系统容量使用率超过90% ({utilization:.2f}%)，建议立即停止部分策略或升级硬件资源",
            "action": "stop_strategies_or_upgrade"
        })
    elif utilization > 80:
        recommendations.append({
            "level": "warning",
            "message": f"系统容量使用率超过80% ({utilization:.2f}%)，建议规划资源升级",
            "action": "plan_upgrade"
        })
    elif utilization > 50:
        recommendations.append({
            "level": "info",
            "message": f"系统容量使用正常 ({utilization:.2f}%)，可继续添加策略",
            "action": "normal_operation"
        })
    else:
        recommendations.append({
            "level": "info",
            "message": f"系统容量充足 ({utilization:.2f}%)，大量可用槽位",
            "action": "normal_operation"
        })

    # 硬件配置建议
    if running <= 5:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 4核CPU + 8GB内存 (个人使用级别)",
            "action": "hardware_recommendation",
            "hardware": {
                "cpu_cores": 4,
                "memory_gb": 8,
                "estimated_memory_usage": f"~{running * 0.4:.1f}GB",
                "estimated_cpu_usage": f"~{running * 2}%"
            }
        })
    elif running <= 20:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 8核CPU + 16GB内存 (小团队级别)",
            "action": "hardware_recommendation",
            "hardware": {
                "cpu_cores": 8,
                "memory_gb": 16,
                "estimated_memory_usage": f"~{running * 0.4:.1f}GB",
                "estimated_cpu_usage": f"~{running * 1.5}%"
            }
        })
    elif running <= 100:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 16核CPU + 64GB内存 (专业团队级别)",
            "action": "hardware_recommendation",
            "hardware": {
                "cpu_cores": 16,
                "memory_gb": 64,
                "estimated_memory_usage": f"~{running * 0.4:.1f}GB",
                "estimated_cpu_usage": f"~{running * 0.6}%"
            }
        })
    else:
        recommendations.append({
            "level": "info",
            "message": "当前配置建议: 32核CPU + 128GB+内存 (机构级别)",
            "action": "hardware_recommendation",
            "hardware": {
                "cpu_cores": 32,
                "memory_gb": 128,
                "estimated_memory_usage": f"~{running * 0.4:.1f}GB",
                "estimated_cpu_usage": f"~{running * 0.3}%"
            }
        })

    return recommendations
```

### 6.3 API使用示例

#### 前端使用示例 (Vue.js)

```javascript
// 获取系统容量信息
async fetchSystemCapacity() {
  try {
    const response = await axios.get('/api/v1/system/capacity');
    const capacity = response.data;

    // 更新UI显示
    this.maxStrategies = capacity.max_strategies;
    this.runningStrategies = capacity.running_strategies;
    this.availableSlots = capacity.available_slots;
    this.utilizationPercent = capacity.utilization_percent;

    // 根据使用率更改显示颜色
    if (capacity.utilization_percent > 90) {
      this.statusColor = 'red';
    } else if (capacity.utilization_percent > 80) {
      this.statusColor = 'orange';
    } else {
      this.statusColor = 'green';
    }

    // 检查是否可以添加更多策略
    this.canAddMore = capacity.can_start_more;

  } catch (error) {
    console.error('Failed to fetch capacity:', error);
  }
}

// 获取详细容量信息（包含建议）
async fetchDetailedCapacity() {
  try {
    const response = await axios.get('/api/v1/system/capacity/detailed');
    const data = response.data;

    // 显示容量信息
    this.capacityInfo = data.capacity;
    this.portPoolStatus = data.port_pool;
    this.gatewayHealth = data.gateway_health;

    // 显示系统建议
    this.recommendations = data.recommendations;

    // 如果有critical级别的建议，显示警告
    const criticalRecommendations = data.recommendations.filter(
      r => r.level === 'critical'
    );
    if (criticalRecommendations.length > 0) {
      this.showCriticalAlert(criticalRecommendations);
    }

  } catch (error) {
    console.error('Failed to fetch detailed capacity:', error);
  }
}

// 获取容量使用趋势
async fetchCapacityTrend(hours = 24) {
  try {
    const response = await axios.get(
      `/api/v1/system/capacity/utilization-trend?hours=${hours}`
    );
    const trendData = response.data;

    // 使用ECharts或其他图表库绘制趋势图
    this.drawCapacityTrendChart(trendData.data_points);

    // 显示趋势统计
    this.currentUtilization = trendData.current_utilization;
    this.peakUtilization = trendData.peak_utilization;
    this.averageUtilization = trendData.average_utilization;
    this.trend = trendData.trend; // stable, increasing, decreasing

  } catch (error) {
    console.error('Failed to fetch capacity trend:', error);
  }
}

// 设置容量告警阈值
async setCapacityAlertThreshold(threshold) {
  try {
    const response = await axios.post(
      '/api/v1/system/capacity/alert-threshold',
      { threshold_percent: threshold }
    );

    if (response.data.status === 'success') {
      this.$message.success(`容量告警阈值已设置为 ${threshold}%`);
    }

  } catch (error) {
    this.$message.error('设置告警阈值失败: ' + error.message);
  }
}

// 定时刷新容量信息（每30秒）
mounted() {
  this.fetchSystemCapacity();
  this.capacityRefreshTimer = setInterval(() => {
    this.fetchSystemCapacity();
  }, 30000); // 30秒刷新一次
}

beforeDestroy() {
  if (this.capacityRefreshTimer) {
    clearInterval(this.capacityRefreshTimer);
  }
}
```

#### 容量监控仪表盘组件示例

```vue
<template>
  <div class="capacity-dashboard">
    <!-- 容量概览卡片 -->
    <el-card class="capacity-overview">
      <div slot="header">
        <span>系统容量监控</span>
        <el-tag :type="statusTagType" style="float: right;">
          {{ statusText }}
        </el-tag>
      </div>

      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ runningStrategies }}</div>
            <div class="stat-label">运行中策略</div>
          </div>
        </el-col>

        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ maxStrategies }}</div>
            <div class="stat-label">最大容量</div>
          </div>
        </el-col>

        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ availableSlots }}</div>
            <div class="stat-label">可用槽位</div>
          </div>
        </el-col>

        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ utilizationPercent.toFixed(2) }}%</div>
            <div class="stat-label">容量使用率</div>
          </div>
        </el-col>
      </el-row>

      <!-- 容量进度条 -->
      <el-progress
        :percentage="utilizationPercent"
        :status="progressStatus"
        :stroke-width="20"
        style="margin-top: 20px;"
      />

      <!-- 端口范围信息 -->
      <div class="port-info" style="margin-top: 20px;">
        <el-tag size="small">端口范围: {{ portRange }}</el-tag>
        <el-tag size="small" type="info" style="margin-left: 10px;">
          架构: {{ architecture }}
        </el-tag>
      </div>
    </el-card>

    <!-- 系统建议卡片 -->
    <el-card class="recommendations" style="margin-top: 20px;">
      <div slot="header">系统建议</div>

      <el-timeline>
        <el-timeline-item
          v-for="(rec, index) in recommendations"
          :key="index"
          :type="getRecommendationType(rec.level)"
          :icon="getRecommendationIcon(rec.level)"
        >
          <p>{{ rec.message }}</p>
          <div v-if="rec.hardware" class="hardware-details">
            <el-tag size="mini">CPU: {{ rec.hardware.cpu_cores }}核</el-tag>
            <el-tag size="mini" style="margin-left: 5px;">
              内存: {{ rec.hardware.memory_gb }}GB
            </el-tag>
            <el-tag size="mini" type="info" style="margin-left: 5px;">
              预估内存使用: {{ rec.hardware.estimated_memory_usage }}
            </el-tag>
            <el-tag size="mini" type="info" style="margin-left: 5px;">
              预估CPU使用: {{ rec.hardware.estimated_cpu_usage }}
            </el-tag>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 容量趋势图表 -->
    <el-card class="capacity-trend" style="margin-top: 20px;">
      <div slot="header">
        <span>容量使用趋势</span>
        <el-radio-group v-model="trendPeriod" size="small" style="float: right;" @change="fetchCapacityTrend">
          <el-radio-button :label="24">24小时</el-radio-button>
          <el-radio-button :label="72">3天</el-radio-button>
          <el-radio-button :label="168">7天</el-radio-button>
        </el-radio-group>
      </div>

      <div ref="trendChart" style="width: 100%; height: 300px;"></div>
    </el-card>

    <!-- 告警阈值设置 -->
    <el-card class="alert-threshold" style="margin-top: 20px;">
      <div slot="header">告警阈值设置</div>

      <el-form label-width="120px">
        <el-form-item label="容量告警阈值">
          <el-slider
            v-model="alertThreshold"
            :min="50"
            :max="95"
            :step="5"
            show-stops
            :marks="{ 50: '50%', 70: '70%', 80: '80%', 90: '90%', 95: '95%' }"
            @change="handleThresholdChange"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="saveAlertThreshold">
            保存设置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'CapacityDashboard',

  data() {
    return {
      runningStrategies: 0,
      maxStrategies: 999,
      availableSlots: 999,
      utilizationPercent: 0,
      portRange: '8081-9080',
      architecture: 'multi_instance_reverse_proxy',
      recommendations: [],
      trendPeriod: 24,
      alertThreshold: 80,
      capacityRefreshTimer: null,
      trendChart: null
    };
  },

  computed: {
    statusText() {
      if (this.utilizationPercent > 90) return '容量紧张';
      if (this.utilizationPercent > 80) return '容量预警';
      if (this.utilizationPercent > 50) return '运行正常';
      return '容量充足';
    },

    statusTagType() {
      if (this.utilizationPercent > 90) return 'danger';
      if (this.utilizationPercent > 80) return 'warning';
      return 'success';
    },

    progressStatus() {
      if (this.utilizationPercent > 90) return 'exception';
      if (this.utilizationPercent > 80) return 'warning';
      return 'success';
    }
  },

  mounted() {
    this.initTrendChart();
    this.fetchDetailedCapacity();
    this.fetchCapacityTrend(this.trendPeriod);

    // 定时刷新
    this.capacityRefreshTimer = setInterval(() => {
      this.fetchDetailedCapacity();
    }, 30000); // 每30秒刷新
  },

  beforeDestroy() {
    if (this.capacityRefreshTimer) {
      clearInterval(this.capacityRefreshTimer);
    }
    if (this.trendChart) {
      this.trendChart.dispose();
    }
  },

  methods: {
    async fetchDetailedCapacity() {
      // 实现见上文
    },

    async fetchCapacityTrend(hours) {
      // 实现见上文
    },

    async saveAlertThreshold() {
      await this.setCapacityAlertThreshold(this.alertThreshold);
    },

    initTrendChart() {
      this.trendChart = echarts.init(this.$refs.trendChart);
      // 配置ECharts选项...
    },

    drawCapacityTrendChart(dataPoints) {
      const option = {
        title: {
          text: '容量使用率趋势'
        },
        tooltip: {
          trigger: 'axis',
          formatter: '{b}<br/>使用率: {c}%'
        },
        xAxis: {
          type: 'category',
          data: dataPoints.map(p => new Date(p.timestamp * 1000).toLocaleTimeString())
        },
        yAxis: {
          type: 'value',
          name: '使用率 (%)',
          min: 0,
          max: 100
        },
        series: [{
          data: dataPoints.map(p => p.utilization),
          type: 'line',
          smooth: true,
          areaStyle: {
            color: 'rgba(24, 144, 255, 0.2)'
          }
        }]
      };

      this.trendChart.setOption(option);
    },

    getRecommendationType(level) {
      const typeMap = {
        'critical': 'danger',
        'warning': 'warning',
        'info': 'primary'
      };
      return typeMap[level] || 'primary';
    },

    getRecommendationIcon(level) {
      const iconMap = {
        'critical': 'el-icon-warning',
        'warning': 'el-icon-warning-outline',
        'info': 'el-icon-info'
      };
      return iconMap[level] || 'el-icon-info';
    }
  }
};
</script>

<style scoped>
.capacity-dashboard {
  padding: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #1890ff;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.port-info {
  text-align: center;
}

.hardware-details {
  margin-top: 10px;
}
</style>
```

### 6.4 容量监控集成到监控服务

```python
# backend/services/monitoring_service.py - 增加容量监控

class EnhancedMonitoringService:
    """增强的监控服务 - 支持FreqTrade多实例架构"""

    def __init__(self):
        self.redis_client = None
        self.freqtrade_manager: FreqTradeGatewayManager = None
        self.api_gateway: FreqTradeAPIGateway = None
        self.monitoring_tasks = {}
        self.config = config_manager.get_monitoring_config()

    async def start_monitoring(self):
        """启动监控服务"""
        # 启动系统状态监控
        self.monitoring_tasks["system"] = asyncio.create_task(
            self._system_status_monitor()
        )

        # 启动策略状态监控（多实例模式）
        self.monitoring_tasks["strategies"] = asyncio.create_task(
            self._multi_instance_strategy_monitor()
        )

        # 启动代理健康检查
        self.monitoring_tasks["proxies"] = asyncio.create_task(
            self._proxy_health_monitor()
        )

        # 启动API Gateway健康检查
        self.monitoring_tasks["gateway"] = asyncio.create_task(
            self._gateway_health_monitor()
        )

        # ✨ 新增：启动容量监控
        self.monitoring_tasks["capacity"] = asyncio.create_task(
            self._capacity_monitor()
        )

    async def _capacity_monitor(self):
        """容量监控 - 定期记录容量使用情况"""
        while True:
            try:
                # 获取当前容量信息
                capacity_info = self.freqtrade_manager.get_capacity_info()

                # 添加时间戳
                capacity_record = {
                    **capacity_info,
                    "timestamp": time.time()
                }

                # 保存到Redis（用于趋势分析）
                await self._save_capacity_record(capacity_record)

                # 检查是否超过告警阈值
                threshold = await self._get_capacity_alert_threshold()
                if capacity_info["utilization_percent"] > threshold:
                    await self._send_capacity_alert(capacity_info, threshold)

                # 每5分钟记录一次
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Capacity monitoring error: {e}")
                await asyncio.sleep(300)

    async def _save_capacity_record(self, capacity_record: dict):
        """保存容量记录到Redis"""
        try:
            # 使用sorted set存储，分数为时间戳
            await self.redis_client.zadd(
                "capacity:history",
                {json.dumps(capacity_record): capacity_record["timestamp"]}
            )

            # 只保留最近7天的数据
            cutoff_time = time.time() - (7 * 24 * 3600)
            await self.redis_client.zremrangebyscore(
                "capacity:history",
                "-inf",
                cutoff_time
            )

        except Exception as e:
            logger.error(f"Failed to save capacity record: {e}")

    async def _get_capacity_alert_threshold(self) -> float:
        """获取容量告警阈值"""
        try:
            threshold = await self.redis_client.get("capacity:alert_threshold")
            if threshold:
                return float(threshold)
            return 80.0  # 默认阈值80%
        except Exception as e:
            logger.error(f"Failed to get alert threshold: {e}")
            return 80.0

    async def _send_capacity_alert(self, capacity_info: dict, threshold: float):
        """发送容量告警"""
        alert_message = {
            "type": "capacity_alert",
            "level": "warning" if capacity_info["utilization_percent"] < 90 else "critical",
            "utilization_percent": capacity_info["utilization_percent"],
            "threshold": threshold,
            "running_strategies": capacity_info["running_strategies"],
            "available_slots": capacity_info["available_slots"],
            "timestamp": time.time(),
            "message": f"系统容量使用率达到 {capacity_info['utilization_percent']:.2f}%，已超过阈值 {threshold}%",
            "architecture": "multi_instance_reverse_proxy"
        }

        # 发送到通知系统
        await self._send_system_alert(alert_message)
```

---

## 7. 总结：999策略扩展完整特性

### 7.1 核心能力

✅ **超大规模并发支持**
- 支持999个FreqTrade策略实例同时运行
- 端口范围: 8081-9080 (999个独立端口)
- 智能端口池管理，自动分配和释放
- 独立进程隔离，故障不互相影响

✅ **智能容量管理**
- 实时容量监控和统计
- 端口池状态追踪
- 容量使用率趋势分析
- 自动容量告警机制

✅ **弹性扩展**
- 运行时动态增减策略
- 无需重启系统
- 优雅的策略启停机制
- 自动端口回收和复用

✅ **性能优化**
- 端口池O(1)时间复杂度操作
- Redis缓存减少数据库压力
- 异步IO提高并发性能
- 资源使用率实时监控

### 7.2 适用场景

| 用户类型 | 策略数量 | 容量占用 | 推荐配置 | 使用场景 |
|---------|---------|---------|---------|---------|
| **个人用户** | 3-5个 | < 1% | 4核 + 8GB | 个人投资，少量策略测试 |
| **小团队** | 10-20个 | < 2% | 8核 + 16GB | 小型量化团队，多策略组合 |
| **专业团队** | 50-100个 | < 10% | 16核 + 64GB | 专业量化机构，策略矩阵 |
| **机构级别** | 100-999个 | < 100% | 32核 + 128GB+ | 大型机构，海量策略并行 |

### 7.3 API端点总览

```
系统容量相关:
GET  /api/v1/system/capacity                    # 获取系统容量信息
GET  /api/v1/system/port-pool                   # 获取端口池状态
GET  /api/v1/system/capacity/detailed           # 获取详细容量和建议
GET  /api/v1/system/capacity/utilization-trend  # 获取容量使用趋势
POST /api/v1/system/capacity/alert-threshold    # 设置容量告警阈值
GET  /api/v1/system/statistics                  # 获取系统统计信息
GET  /api/v1/system/health                      # 系统健康检查

配置管理相关:
GET  /api/v1/system/config/{config_name}        # 获取配置信息
POST /api/v1/system/config/reload               # 重新加载配置

策略管理相关:
GET  /api/v1/strategies/overview                # 获取所有策略概览
GET  /api/v1/strategies/gateway/status          # 获取Gateway状态
POST /api/v1/strategies/{id}/start              # 启动策略
POST /api/v1/strategies/{id}/stop               # 停止策略
```

### 7.4 技术优势总结

**1. 架构优势**
- 反向代理模式：内部多端口 + 外部统一入口
- 进程隔离：单个策略故障不影响整体
- 弹性扩展：支持运行时动态调整
- 高可用性：Gateway自动健康检查和故障转移

**2. 运维优势**
- 统一监控：所有策略状态集中管理
- 智能告警：容量、性能、健康状态多维度监控
- 可视化：完整的前端仪表盘和趋势图表
- 易维护：配置文件统一管理，热重载支持

**3. 性能优势**
- 并发执行：充分利用多核CPU资源
- 资源隔离：每个策略独立内存空间
- 缓存优化：Redis缓存减少数据库访问
- 异步架构：高并发处理能力

**4. 扩展优势**
- 从个人使用(3-5策略)到机构级别(100-999策略)无缝扩展
- 智能容量建议系统
- 自动化的端口管理
- 完善的监控和告警机制

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"activeForm": "\u5206\u6790\u7528\u6237\u9700\u6c42\u8c03\u7814\u7ed3\u679c", "content": "\u5206\u6790\u7528\u6237\u9700\u6c42\u8c03\u7814\u7ed3\u679c", "status": "completed"}, {"activeForm": "\u8bbe\u8ba1\u6838\u5fc3\u4e1a\u52a1\u6d41\u7a0b", "content": "\u8bbe\u8ba1\u6838\u5fc3\u4e1a\u52a1\u6d41\u7a0b", "status": "completed"}, {"activeForm": "\u5236\u5b9a\u8be6\u7ec6\u7684\u9875\u9762\u539f\u578b\u548c\u529f\u80fd\u89c4\u8303", "content": "\u5236\u5b9a\u8be6\u7ec6\u7684\u9875\u9762\u539f\u578b\u548c\u529f\u80fd\u89c4\u8303", "status": "completed"}, {"activeForm": "\u6839\u636e\u7528\u6237\u4fee\u6539\u610f\u89c1\u66f4\u65b0\u4e1a\u52a1\u6d41\u7a0b\u8bbe\u8ba1", "content": "\u6839\u636e\u7528\u6237\u4fee\u6539\u610f\u89c1\u66f4\u65b0\u4e1a\u52a1\u6d41\u7a0b\u8bbe\u8ba1", "status": "completed"}, {"activeForm": "\u4f18\u5316\u4fe1\u53f7\u5f3a\u5ea6\u8ba1\u7b97\u548c\u914d\u7f6e\u754c\u9762\u8bbe\u8ba1", "content": "\u4f18\u5316\u4fe1\u53f7\u5f3a\u5ea6\u8ba1\u7b97\u548c\u914d\u7f6e\u754c\u9762\u8bbe\u8ba1", "status": "completed"}, {"activeForm": "\u6dfb\u52a0\u9608\u503c\u914d\u7f6e\u5d4c\u5165\u548c\u5206\u9875\u63a7\u5236\u529f\u80fd", "content": "\u6dfb\u52a0\u9608\u503c\u914d\u7f6e\u5d4c\u5165\u548c\u5206\u9875\u63a7\u5236\u529f\u80fd", "status": "completed"}, {"activeForm": "\u8bbe\u8ba1FreqTrade\u7248\u672c\u7ba1\u7406\u7cfb\u7edf", "content": "\u8bbe\u8ba1FreqTrade\u7248\u672c\u7ba1\u7406\u7cfb\u7edf", "status": "completed"}, {"activeForm": "\u8bbe\u8ba1API\u63a5\u53e3\u89c4\u8303\u548c\u6570\u636e\u7ed3\u6784", "content": "\u8bbe\u8ba1API\u63a5\u53e3\u89c4\u8303\u548c\u6570\u636e\u7ed3\u6784", "status": "completed"}, {"activeForm": "\u5206\u6790\u6280\u672f\u51b3\u7b56\u548c\u63d0\u51fa\u8ba8\u8bba\u5efa\u8bae", "content": "\u5206\u6790\u6280\u672f\u51b3\u7b56\u548c\u63d0\u51fa\u8ba8\u8bba\u5efa\u8bae", "status": "completed"}, {"activeForm": "\u6839\u636e\u7528\u6237\u786e\u8ba4\u8c03\u6574\u6280\u672f\u65b9\u6848", "content": "\u6839\u636e\u7528\u6237\u786e\u8ba4\u8c03\u6574\u6280\u672f\u65b9\u6848", "status": "completed"}, {"activeForm": "\u521b\u5efa\u6280\u672f\u5b9e\u73b0\u7ec6\u8282\u6587\u6863", "content": "\u521b\u5efa\u6280\u672f\u5b9e\u73b0\u7ec6\u8282\u6587\u6863", "status": "in_progress"}]