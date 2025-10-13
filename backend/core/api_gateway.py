"""
FreqTrade API Gateway - Unified Entry Point
Routes requests to individual FreqTrade strategy instances
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import aiohttp
import json
import asyncio
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FreqTradeAPIGateway:
    """FreqTrade API网关 - 统一端口路由管理"""

    def __init__(self, gateway_port: int = 8080):
        self.gateway_port = gateway_port
        self.app = FastAPI(title="FreqTrade API Gateway")
        self.routes_config: Dict[str, dict] = {}  # strategy_id -> upstream_config
        self.routes_file = Path("/app/gateway_routes.json")
        self.setup_routes()

    def setup_routes(self):
        """设置API Gateway路由规则"""

        # 1. 策略特定路由: /api/strategy/{strategy_id}/*
        @self.app.api_route(
            "/api/strategy/{strategy_id:int}/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE"]
        )
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
            strategy_key = str(strategy_id)
            if strategy_key not in self.routes_config:
                raise HTTPException(
                    status_code=404,
                    detail=f"Strategy {strategy_id} not found"
                )

            # 2. 获取上游服务地址
            upstream_config = self.routes_config[strategy_key]
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
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gateway routing error: {e}", exc_info=True)
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
            if self.routes_file.exists():
                with open(self.routes_file, 'r') as f:
                    self.routes_config = json.load(f)

                logger.info(f"Reloaded {len(self.routes_config)} routes")
                return {
                    "status": "success",
                    "routes_count": len(self.routes_config),
                    "message": "Routes configuration reloaded successfully"
                }
            else:
                logger.warning("Routes file not found, using empty configuration")
                self.routes_config = {}
                return {
                    "status": "success",
                    "routes_count": 0,
                    "message": "No routes file found, initialized with empty configuration"
                }
        except Exception as e:
            logger.error(f"Failed to reload routes: {e}", exc_info=True)
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
