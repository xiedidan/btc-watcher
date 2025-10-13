"""
Configuration Manager
Manages system configuration from YAML files
"""
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
                    config_name = config_file.replace('.yml', '')
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
