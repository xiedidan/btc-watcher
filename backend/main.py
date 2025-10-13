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
from api.v1 import system, strategies, signals, auth, monitoring, notifications
from core.freqtrade_manager import FreqTradeGatewayManager
from services.monitoring_service import MonitoringService
from services.notification_service import NotificationService

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
        # 将manager注入到strategies模块
        strategies._ft_manager = freqtrade_manager
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

    # TODO: Connect to Redis

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

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

    # TODO: Close database connections
    # TODO: Close Redis connections

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
