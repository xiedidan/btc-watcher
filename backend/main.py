"""
BTC Watcher Backend Main Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from config import settings
from database.session import engine, Base, get_db, SessionLocal
from api.v1 import system, strategies, signals, auth, monitoring, notifications, websocket, proxies, settings as settings_api
from api.v1 import market, config as config_api, health, notify, realtime, heartbeat
from core.freqtrade_manager import FreqTradeGatewayManager
from services.monitoring_service import MonitoringService
from services.notification_service import NotificationService
from services.notifyhub.core import notify_hub
from app.websocket.monitoring_broadcaster import MonitoringBroadcaster
from app.websocket.manager import manager as ws_manager
from core.redis_client import redis_client
from services.token_cache import TokenCacheService
import services.token_cache as token_cache_module
from services.ccxt_manager import CCXTManager
from services.exchange_failover_manager import ExchangeFailoverManager
from services.rate_limit_handler import RateLimitHandler
from services.market_data_scheduler import MarketDataScheduler
from services.system_config_service import SystemConfigService
from services.log_monitor_service import LogMonitorService
import services.log_monitor_service as log_monitor_module
from services.heartbeat_monitor_service import StrategyHeartbeatMonitor
import services.heartbeat_monitor_service as heartbeat_monitor_module
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
freqtrade_manager: FreqTradeGatewayManager = None
monitoring_service: MonitoringService = None
notification_service: NotificationService = None
monitoring_broadcaster: MonitoringBroadcaster = None
ccxt_manager: CCXTManager = None
exchange_failover_manager: ExchangeFailoverManager = None
rate_limit_handler: RateLimitHandler = None
market_data_scheduler: MarketDataScheduler = None
log_monitor_service_instance: LogMonitorService = None
heartbeat_monitor_instance: StrategyHeartbeatMonitor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global freqtrade_manager

    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

    # Initialize FreqTrade manager
    try:
        freqtrade_manager = FreqTradeGatewayManager()
        # 将manager注入到strategies和system模块
        strategies._ft_manager = freqtrade_manager
        system._ft_manager = freqtrade_manager
        logger.info("FreqTrade Gateway Manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize FreqTrade manager: {e}")

    # Initialize Log Monitor Service
    global log_monitor_service_instance
    try:
        if freqtrade_manager:
            logs_path = freqtrade_manager.logs_path
            log_monitor_service_instance = LogMonitorService(logs_path)
            log_monitor_service_instance.start()
            # 将服务注入到log_monitor_service模块
            log_monitor_module.log_monitor_service = log_monitor_service_instance
            logger.info(f"✅ Log Monitor Service initialized (watching: {logs_path})")
        else:
            logger.warning("Log Monitor Service not initialized (FreqTrade manager unavailable)")
    except Exception as e:
        logger.error(f"Failed to initialize Log Monitor Service: {e}", exc_info=True)

    # Initialize Heartbeat Monitor Service
    global heartbeat_monitor_instance
    try:
        if freqtrade_manager:
            heartbeat_monitor_instance = StrategyHeartbeatMonitor(
                strategy_manager=freqtrade_manager,
                notify_hub=notify_hub,
                check_interval=30  # 30秒检查一次
            )
            await heartbeat_monitor_instance.start()
            # 将服务注入到heartbeat_monitor_service模块
            heartbeat_monitor_module.heartbeat_monitor = heartbeat_monitor_instance
            logger.info("✅ Heartbeat Monitor Service initialized")
        else:
            logger.warning("Heartbeat Monitor Service not initialized (FreqTrade manager unavailable)")
    except Exception as e:
        logger.error(f"Failed to initialize Heartbeat Monitor Service: {e}", exc_info=True)

    # Strategy Recovery - 智能恢复运行中的策略
    if settings.AUTO_RECOVER_STRATEGIES and freqtrade_manager:
        try:
            # 获取数据库session
            db_gen = get_db()
            db = await db_gen.__anext__()

            logger.info("="*60)
            logger.info("Starting Strategy Recovery (AUTO_RECOVER_STRATEGIES=True)")
            logger.info("="*60)

            # ⭐ 步骤1: 同步实际运行的进程状态（自动恢复机制）
            logger.info("Phase 1: Synchronizing actual process status with database...")
            sync_results = await freqtrade_manager.sync_strategy_status(db)

            # 记录同步结果
            if sync_results["scanned_processes"] > 0:
                logger.info("📊 Status Synchronization Results:")
                logger.info(f"   🔍 Scanned processes: {sync_results['scanned_processes']}")
                logger.info(f"   🔄 Registered orphans: {sync_results['registered_orphans']}")
                logger.info(f"   🧟 Killed zombies: {sync_results['killed_zombies']}")
                logger.info(f"   ✅ Synced to running: {sync_results['synced_to_running']}")
                logger.info(f"   ⏸️  Synced to stopped: {sync_results['synced_to_stopped']}")

                if sync_results["errors"]:
                    logger.warning(f"   ⚠️  Errors: {len(sync_results['errors'])}")
                    for error in sync_results["errors"][:3]:  # Show first 3 errors
                        logger.warning(f"      - {error}")

            # ⭐ 步骤2: 恢复数据库中标记为 running 但实际未运行的策略
            logger.info("\nPhase 2: Recovering strategies marked as 'running' in database...")
            recovery_results = await freqtrade_manager.recover_running_strategies(
                db,
                max_retries=settings.MAX_RECOVERY_RETRIES
            )

            # 记录恢复结果
            if recovery_results["total_found"] > 0:
                logger.info("📊 Recovery Results:")
                logger.info(f"   ✅ Recovered: {recovery_results['recovered']}")
                logger.info(f"   ❌ Failed: {recovery_results['failed']}")
                logger.info(f"   🔄 Reset: {recovery_results['reset']}")

                # 如果有恢复失败的策略，记录详情
                if recovery_results['failed'] > 0:
                    logger.warning("⚠️  Some strategies could not be recovered and were reset to 'stopped'")
                    for detail in recovery_results['details']:
                        if detail['status'] == 'failed_and_reset':
                            logger.warning(f"   - Strategy {detail['strategy_id']} ({detail['name']})")
            else:
                logger.info("✅ No strategies needed recovery")

            logger.info("="*60)

            # 启动日志监控for已恢复的运行中策略
            if log_monitor_service_instance and recovery_results.get('recovered', 0) > 0:
                logger.info("Starting log monitoring for recovered strategies...")
                for detail in recovery_results.get('details', []):
                    if detail['status'] == 'recovered':
                        strategy_id = detail['strategy_id']
                        await log_monitor_service_instance.start_monitoring_strategy(strategy_id)
                        logger.info(f"  ✅ Started monitoring strategy {strategy_id}")
                logger.info("Log monitoring setup complete for recovered strategies")

            # 关闭数据库session
            try:
                await db_gen.aclose()
            except:
                pass

        except Exception as e:
            logger.error(f"Strategy recovery failed: {e}", exc_info=True)
            logger.warning("Continuing startup without strategy recovery...")
    elif not settings.AUTO_RECOVER_STRATEGIES:
        # 如果禁用了自动恢复，重置所有策略状态
        try:
            db_gen = get_db()
            db = await db_gen.__anext__()

            logger.info("="*60)
            logger.info("AUTO_RECOVER_STRATEGIES=False - Resetting all strategies")
            logger.info("="*60)

            reset_count = await freqtrade_manager.reset_all_strategies_status(db)
            logger.info(f"✅ Reset {reset_count} strategies to 'stopped' status")
            logger.info("="*60)

            # 关闭数据库session
            try:
                await db_gen.aclose()
            except:
                pass

        except Exception as e:
            logger.error(f"Failed to reset strategy statuses: {e}", exc_info=True)

    # 扫描所有正在运行的策略并启动日志监控和心跳监控
    if (log_monitor_service_instance or heartbeat_monitor_instance) and freqtrade_manager:
        try:
            logger.info("Scanning for running strategies to monitor logs and heartbeats...")
            db_gen = get_db()
            db = await db_gen.__anext__()

            # 查询所有运行中的策略
            from sqlalchemy import select
            from models.strategy import Strategy
            result = await db.execute(
                select(Strategy).where(Strategy.status == 'running')
            )
            running_strategies = result.scalars().all()

            if running_strategies:
                logger.info(f"Found {len(running_strategies)} running strategies")
                for strategy in running_strategies:
                    # 启动日志监控
                    if log_monitor_service_instance:
                        await log_monitor_service_instance.start_monitoring_strategy(strategy.id)
                        logger.info(f"  ✅ Started log monitoring for strategy {strategy.id} ({strategy.name})")

                    # 注册心跳监控
                    if heartbeat_monitor_instance:
                        log_file_path = str(freqtrade_manager.logs_path / f"strategy_{strategy.id}.log")
                        await heartbeat_monitor_instance.register_strategy(
                            strategy_id=strategy.id,
                            log_file_path=log_file_path
                        )
                        logger.info(f"  ✅ Registered heartbeat monitoring for strategy {strategy.id} ({strategy.name})")

                logger.info("Log and heartbeat monitoring setup complete")
            else:
                logger.info("No running strategies found to monitor")

            # 关闭数据库session
            try:
                await db_gen.aclose()
            except:
                pass

        except Exception as e:
            logger.error(f"Failed to scan and monitor running strategies: {e}", exc_info=True)

    # Initialize monitoring service
    try:
        monitoring_service = MonitoringService(freqtrade_manager)
        await monitoring_service.start()
        # 将服务注入到system模块
        system._monitoring_service = monitoring_service
        logger.info("Monitoring service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring service: {e}")

    # Initialize notification service
    try:
        notification_service = NotificationService()
        await notification_service.start()
        # 将服务注入到notifications模块
        notifications._notification_service = notification_service
        logger.info("Notification service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize notification service: {e}")

    # Initialize NotifyHub
    try:
        await notify_hub.start()
        # 将服务注入到notify模块
        notify._notify_hub = notify_hub
        logger.info("✅ NotifyHub initialized and started")
    except Exception as e:
        logger.error(f"Failed to initialize NotifyHub: {e}")

    # Initialize monitoring broadcaster
    try:
        monitoring_broadcaster = MonitoringBroadcaster(monitoring_service)
        await monitoring_broadcaster.start()
        # 将broadcaster注入到websocket模块
        import app.websocket.monitoring_broadcaster as mb_module
        mb_module.broadcaster = monitoring_broadcaster
        logger.info("Monitoring broadcaster initialized")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring broadcaster: {e}")

    # Initialize Redis connection
    try:
        await redis_client.connect()
        logger.info("✅ Redis client initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis initialization failed: {e}")
        logger.warning("Token caching will be disabled")

    # Initialize Token Cache service
    try:
        if redis_client.is_connected():
            token_cache_service = TokenCacheService(redis_client)
            token_cache_module.token_cache_service = token_cache_service
            logger.info("✅ Token cache service initialized")
        else:
            logger.warning("Token cache service not initialized (Redis unavailable)")
    except Exception as e:
        logger.error(f"Failed to initialize token cache service: {e}")

    # Start WebSocket heartbeat checker
    try:
        await ws_manager.start_heartbeat_checker()
        logger.info("✅ WebSocket heartbeat checker started")
    except Exception as e:
        logger.error(f"Failed to start WebSocket heartbeat checker: {e}")

    # Initialize Market Data Services
    global ccxt_manager, exchange_failover_manager, rate_limit_handler, market_data_scheduler

    try:
        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()

        # Initialize CCXT Manager
        ccxt_manager = CCXTManager(db)
        market._ccxt_manager = ccxt_manager
        logger.info("✅ CCXT Manager initialized")

        # Initialize System Config Service
        config_service = SystemConfigService(db)
        market_config = await config_service.get_market_data_config()

        # Initialize Exchange Failover Manager
        exchange_failover_manager = ExchangeFailoverManager(
            db,
            ccxt_manager,
            market_config.get("enabled_exchanges", ["binance"])
        )
        health._failover_manager = exchange_failover_manager
        # Start health check loop
        await exchange_failover_manager.start_health_check_loop()
        logger.info("✅ Exchange Failover Manager initialized")

        # Initialize Rate Limit Handler
        rate_limit_handler = RateLimitHandler(
            db,
            redis_client,
            ccxt_manager,
            exchange_failover_manager,
            market_config.get("cache_config", {}).get("ttl")
        )
        market._rate_limit_handler = rate_limit_handler
        logger.info("✅ Rate Limit Handler initialized")

        # Initialize Market Data Scheduler
        market_data_scheduler = MarketDataScheduler(
            db,
            rate_limit_handler,
            config_service,
            session_factory=SessionLocal  # Pass session factory for concurrent operations
        )
        await market_data_scheduler.initialize()
        market._market_data_scheduler = market_data_scheduler
        health._market_data_scheduler = market_data_scheduler
        logger.info("✅ Market Data Scheduler initialized")

        # Start scheduler automatically
        if market_config.get("auto_start_scheduler", False):
            await market_data_scheduler.start()
            logger.info("✅ Market Data Scheduler started automatically")

    except Exception as e:
        logger.error(f"Failed to initialize market data services: {e}")
        logger.warning("Market data services will not be available")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop market data scheduler
    if market_data_scheduler:
        try:
            await market_data_scheduler.stop()
            logger.info("Market Data Scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop Market Data Scheduler: {e}")

    # Stop exchange failover health check loop
    if exchange_failover_manager:
        try:
            await exchange_failover_manager.stop_health_check_loop()
            logger.info("Exchange Failover Manager stopped")
        except Exception as e:
            logger.error(f"Failed to stop Exchange Failover Manager: {e}")

    # Close CCXT exchange connections
    if ccxt_manager:
        try:
            await ccxt_manager.close_all_exchanges()
            logger.info("CCXT Manager closed all exchanges")
        except Exception as e:
            logger.error(f"Failed to close CCXT exchanges: {e}")

    # Stop WebSocket heartbeat checker
    try:
        await ws_manager.stop_heartbeat_checker()
        logger.info("WebSocket heartbeat checker stopped")
    except Exception as e:
        logger.error(f"Failed to stop WebSocket heartbeat checker: {e}")

    # Stop monitoring broadcaster
    if monitoring_broadcaster:
        try:
            await monitoring_broadcaster.stop()
            logger.info("Monitoring broadcaster stopped")
        except Exception as e:
            logger.error(f"Failed to stop monitoring broadcaster: {e}")

    # Stop monitoring service
    if monitoring_service:
        try:
            await monitoring_service.stop()
            logger.info("Monitoring service stopped")
        except Exception as e:
            logger.error(f"Failed to stop monitoring service: {e}")

    # Stop notification service
    if notification_service:
        try:
            await notification_service.stop()
            logger.info("Notification service stopped")
        except Exception as e:
            logger.error(f"Failed to stop notification service: {e}")

    # Stop NotifyHub
    try:
        await notify_hub.stop()
        logger.info("✅ NotifyHub stopped")
    except Exception as e:
        logger.error(f"Failed to stop NotifyHub: {e}")

    # Stop all running strategies
    if freqtrade_manager:
        try:
            await freqtrade_manager.stop_all_strategies()
            logger.info("All strategies stopped")
        except Exception as e:
            logger.error(f"Failed to stop strategies: {e}")

    # Close Redis connection
    try:
        await redis_client.disconnect()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Failed to close Redis connection: {e}")

    # Close database connections
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Failed to close database connections: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Cryptocurrency Signal Monitoring and Analysis System",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log request
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed in {duration:.3f}s with status {response.status_code}"
    )

    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production"
    }


# Include routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)

app.include_router(
    strategies.router,
    prefix="/api/v1/strategies",
    tags=["strategies"]
)

app.include_router(
    signals.router,
    prefix="/api/v1/signals",
    tags=["signals"]
)

# Register config router first to match specific routes before catch-all
app.include_router(
    config_api.router,
    prefix="/api/v1/system",
    tags=["config"]
)

app.include_router(
    system.router,
    prefix="/api/v1/system",
    tags=["system"]
)

app.include_router(
    monitoring.router,
    prefix="/api/v1/monitoring",
    tags=["monitoring"]
)

app.include_router(
    notifications.router,
    prefix="/api/v1/notifications",
    tags=["notifications"]
)

app.include_router(
    notify.router,
    prefix="/api/v1/notify",
    tags=["notify"]
)

app.include_router(
    proxies.router,
    prefix="/api/v1/proxies",
    tags=["proxies"]
)

app.include_router(
    settings_api.router,
    prefix="/api/v1/settings",
    tags=["settings"]
)

app.include_router(
    websocket.router,
    prefix="/api/v1",
    tags=["websocket"]
)

app.include_router(
    market.router,
    prefix="/api/v1",
    tags=["market"]
)

app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["health"]
)

app.include_router(
    realtime.router,
    prefix="/api/v1/realtime",
    tags=["realtime"]
)

app.include_router(
    heartbeat.router,
    prefix="/api/v1",
    tags=["heartbeat"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
