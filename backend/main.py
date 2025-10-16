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
from database.session import engine, Base
from api.v1 import system, strategies, signals, auth, monitoring, notifications, websocket, proxies, settings as settings_api
from core.freqtrade_manager import FreqTradeGatewayManager
from services.monitoring_service import MonitoringService
from services.notification_service import NotificationService
from app.websocket.monitoring_broadcaster import MonitoringBroadcaster
from core.redis_client import redis_client
from services.token_cache import TokenCacheService
import services.token_cache as token_cache_module

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

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
