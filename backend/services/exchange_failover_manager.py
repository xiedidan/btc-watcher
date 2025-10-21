"""
Exchange Failover Manager Service
Manages automatic exchange failover and health monitoring
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from services.ccxt_manager import CCXTManager

logger = logging.getLogger(__name__)


class ExchangeHealth:
    """Exchange health status tracker"""

    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.is_healthy = True
        self.health_score = 100  # 0-100
        self.last_check_time: Optional[datetime] = None
        self.failure_count = 0
        self.consecutive_failures = 0
        self.last_success_time: Optional[datetime] = None
        self.last_failure_time: Optional[datetime] = None
        self.error_message: Optional[str] = None

    def mark_success(self):
        """Mark successful operation"""
        self.last_success_time = datetime.now()
        self.consecutive_failures = 0
        self.is_healthy = True
        # Gradually recover health score
        self.health_score = min(100, self.health_score + 10)

    def mark_failure(self, error_message: str):
        """Mark failed operation"""
        self.last_failure_time = datetime.now()
        self.failure_count += 1
        self.consecutive_failures += 1
        self.error_message = error_message

        # Reduce health score
        self.health_score = max(0, self.health_score - 20)

        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "exchange_name": self.exchange_name,
            "is_healthy": self.is_healthy,
            "health_score": self.health_score,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "error_message": self.error_message
        }


class ExchangeFailoverManager:
    """Automatic exchange failover manager"""

    def __init__(self, db: AsyncSession, ccxt_manager: CCXTManager, enabled_exchanges: List[str]):
        self.db = db
        self.ccxt_manager = ccxt_manager
        self.enabled_exchanges = enabled_exchanges
        self.exchange_health: Dict[str, ExchangeHealth] = {}
        self.current_exchange = enabled_exchanges[0] if enabled_exchanges else None
        self.health_check_interval = 300  # 5 minutes
        self._health_check_task: Optional[asyncio.Task] = None

        # Initialize health trackers
        for exchange in enabled_exchanges:
            self.exchange_health[exchange] = ExchangeHealth(exchange)

    async def get_healthy_exchange(self, preferred_exchange: Optional[str] = None) -> Optional[str]:
        """
        Get a healthy exchange for data fetching

        Args:
            preferred_exchange: Preferred exchange to use if healthy

        Returns:
            Exchange name or None if all unhealthy
        """
        # Try preferred exchange first
        if preferred_exchange and preferred_exchange in self.exchange_health:
            if self.exchange_health[preferred_exchange].is_healthy:
                return preferred_exchange

        # Try current exchange
        if self.current_exchange and self.exchange_health[self.current_exchange].is_healthy:
            return self.current_exchange

        # Find best healthy exchange by health score
        healthy_exchanges = [
            (name, health.health_score)
            for name, health in self.exchange_health.items()
            if health.is_healthy
        ]

        if not healthy_exchanges:
            logger.error("No healthy exchanges available")
            return None

        # Sort by health score descending
        healthy_exchanges.sort(key=lambda x: x[1], reverse=True)
        best_exchange = healthy_exchanges[0][0]

        # Update current exchange if changed
        if best_exchange != self.current_exchange:
            logger.info(f"Switching from {self.current_exchange} to {best_exchange}")
            self.current_exchange = best_exchange

        return best_exchange

    async def mark_exchange_result(self, exchange_name: str, success: bool, error_message: str = ""):
        """
        Mark exchange operation result

        Args:
            exchange_name: Exchange name
            success: Whether operation was successful
            error_message: Error message if failed
        """
        if exchange_name not in self.exchange_health:
            logger.warning(f"Unknown exchange: {exchange_name}")
            return

        health = self.exchange_health[exchange_name]

        if success:
            health.mark_success()
            logger.debug(f"Exchange {exchange_name} operation successful, health score: {health.health_score}")
        else:
            health.mark_failure(error_message)
            logger.warning(
                f"Exchange {exchange_name} operation failed: {error_message}, "
                f"consecutive failures: {health.consecutive_failures}, "
                f"health score: {health.health_score}"
            )

            # Trigger failover if exchange became unhealthy
            if not health.is_healthy and exchange_name == self.current_exchange:
                await self._trigger_failover()

    async def _trigger_failover(self):
        """Trigger failover to healthy exchange"""
        logger.warning(f"Triggering failover from {self.current_exchange}")

        # Get new healthy exchange
        new_exchange = await self.get_healthy_exchange()

        if new_exchange:
            logger.info(f"Failover completed: {self.current_exchange} -> {new_exchange}")
        else:
            logger.error("Failover failed: No healthy exchanges available")

    async def check_all_exchanges_health(self) -> Dict[str, Dict]:
        """
        Check health of all enabled exchanges

        Returns:
            Dictionary of exchange health status
        """
        logger.info("Starting health check for all exchanges")
        results = {}

        for exchange_name in self.enabled_exchanges:
            try:
                # Test exchange connection
                is_healthy = await self.ccxt_manager.test_exchange_connection(exchange_name)

                # Update health status
                health = self.exchange_health[exchange_name]
                health.last_check_time = datetime.now()

                if is_healthy:
                    health.mark_success()
                else:
                    health.mark_failure("Connection test failed")

                results[exchange_name] = health.to_dict()

            except Exception as e:
                logger.error(f"Health check failed for {exchange_name}: {e}")
                self.exchange_health[exchange_name].mark_failure(str(e))
                results[exchange_name] = self.exchange_health[exchange_name].to_dict()

        logger.info("Health check completed for all exchanges")
        return results

    async def start_health_check_loop(self):
        """Start periodic health check loop"""
        if self._health_check_task and not self._health_check_task.done():
            logger.warning("Health check loop already running")
            return

        logger.info(f"Starting health check loop (interval: {self.health_check_interval}s)")
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_check_loop(self):
        """Stop periodic health check loop"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                logger.info("Health check loop stopped")

    async def _health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                await self.check_all_exchanges_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)

    def get_all_health_status(self) -> Dict[str, Dict]:
        """
        Get health status of all exchanges

        Returns:
            Dictionary of exchange health status
        """
        return {
            name: health.to_dict()
            for name, health in self.exchange_health.items()
        }

    def get_current_exchange(self) -> Optional[str]:
        """
        Get current active exchange

        Returns:
            Current exchange name
        """
        return self.current_exchange

    def is_auto_failover_needed(self) -> bool:
        """
        Check if auto failover is needed

        Returns:
            True if current exchange is unhealthy
        """
        if not self.current_exchange:
            return True

        current_health = self.exchange_health.get(self.current_exchange)
        return current_health and not current_health.is_healthy


async def get_exchange_failover_manager(
    db: AsyncSession,
    ccxt_manager: CCXTManager,
    enabled_exchanges: List[str]
) -> ExchangeFailoverManager:
    """
    Factory function for ExchangeFailoverManager

    Args:
        db: Database session
        ccxt_manager: CCXT manager instance
        enabled_exchanges: List of enabled exchanges

    Returns:
        ExchangeFailoverManager instance
    """
    return ExchangeFailoverManager(db, ccxt_manager, enabled_exchanges)
