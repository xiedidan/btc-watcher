"""
时间规则管理器
Time Rule Manager - 管理勿扰时段、工作时间等
"""
from datetime import datetime, time as dt_time
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class TimeRuleManager:
    """时间规则管理器 - 管理勿扰时段、工作时间等"""

    async def should_send_at_current_time(
        self,
        time_rule: Optional[dict],
        priority: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查当前时间是否应该发送通知

        Args:
            time_rule: 时间规则配置
            priority: 优先级 (P0/P1/P2)

        Returns:
            Tuple[bool, Optional[str]]: (是否发送, 原因)
        """
        if not time_rule or not time_rule.get("enabled", False):
            return True, None

        now = datetime.now()

        # 1. 勿扰时段检查
        if time_rule.get("quiet_hours_enabled", False):
            is_quiet, reason = self._check_quiet_hours(now, time_rule, priority)
            if not is_quiet:
                return False, reason

        # 2. 工作时间检查
        if time_rule.get("working_hours_enabled", False):
            is_working, reason = self._check_working_hours(now, time_rule)
            if not is_working:
                return False, reason

        # 3. 周末模式检查
        if time_rule.get("weekend_mode_enabled", False):
            is_weekend_ok, reason = self._check_weekend_mode(now, time_rule, priority)
            if not is_weekend_ok:
                return False, reason

        # 4. 假期模式检查
        if time_rule.get("holiday_mode_enabled", False):
            is_holiday_ok, reason = self._check_holiday_mode(now, time_rule)
            if not is_holiday_ok:
                return False, reason

        return True, None

    def _check_quiet_hours(
        self,
        now: datetime,
        time_rule: dict,
        priority: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查勿扰时段

        Args:
            now: 当前时间
            time_rule: 时间规则
            priority: 优先级

        Returns:
            Tuple[bool, Optional[str]]: (是否允许发送, 原因)
        """
        if not time_rule.get("quiet_hours_enabled", False):
            return True, None

        current_time = now.time()
        quiet_start_str = time_rule.get("quiet_start_time", "22:00")
        quiet_end_str = time_rule.get("quiet_end_time", "08:00")
        quiet_priority_filter = time_rule.get("quiet_priority_filter", "P2")

        try:
            start_time = datetime.strptime(quiet_start_str, "%H:%M").time()
            end_time = datetime.strptime(quiet_end_str, "%H:%M").time()
        except ValueError:
            logger.error(f"Invalid quiet hours time format: {quiet_start_str} - {quiet_end_str}")
            return True, None

        is_in_quiet_hours = self._is_time_in_range(current_time, start_time, end_time)

        if is_in_quiet_hours:
            # 勿扰时段只发送高优先级通知
            if self._is_priority_lower(priority, quiet_priority_filter):
                return False, f"quiet_hours: only {quiet_priority_filter}+ allowed"

        return True, None

    def _check_working_hours(
        self,
        now: datetime,
        time_rule: dict
    ) -> Tuple[bool, Optional[str]]:
        """
        检查工作时间

        Args:
            now: 当前时间
            time_rule: 时间规则

        Returns:
            Tuple[bool, Optional[str]]: (是否在工作时间, 原因)
        """
        if not time_rule.get("working_hours_enabled", False):
            return True, None

        current_time = now.time()
        current_weekday = now.isoweekday()  # 1=Monday, 7=Sunday

        working_days = time_rule.get("working_days", [1, 2, 3, 4, 5])
        working_start_str = time_rule.get("working_start_time", "09:00")
        working_end_str = time_rule.get("working_end_time", "18:00")

        # 检查是否工作日
        if current_weekday not in working_days:
            return False, "outside_working_days"

        try:
            start_time = datetime.strptime(working_start_str, "%H:%M").time()
            end_time = datetime.strptime(working_end_str, "%H:%M").time()
        except ValueError:
            logger.error(f"Invalid working hours time format: {working_start_str} - {working_end_str}")
            return True, None

        is_in_working_hours = self._is_time_in_range(current_time, start_time, end_time)

        if not is_in_working_hours:
            return False, "outside_working_hours"

        return True, None

    def _check_weekend_mode(
        self,
        now: datetime,
        time_rule: dict,
        priority: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查周末模式

        Args:
            now: 当前时间
            time_rule: 时间规则
            priority: 优先级

        Returns:
            Tuple[bool, Optional[str]]: (是否允许发送, 原因)
        """
        if not time_rule.get("weekend_mode_enabled", False):
            return True, None

        is_weekend = now.isoweekday() in [6, 7]  # Saturday, Sunday

        if is_weekend:
            # 周末将P1降级为P0
            if time_rule.get("weekend_downgrade_p1_to_p0", True) and priority == "P1":
                return False, "weekend_downgrade_p1_to_p0"

        return True, None

    def _check_holiday_mode(
        self,
        now: datetime,
        time_rule: dict
    ) -> Tuple[bool, Optional[str]]:
        """
        检查假期模式

        Args:
            now: 当前时间
            time_rule: 时间规则

        Returns:
            Tuple[bool, Optional[str]]: (是否允许发送, 原因)
        """
        if not time_rule.get("holiday_mode_enabled", False):
            return True, None

        current_date = now.strftime("%Y-%m-%d")
        holiday_dates = time_rule.get("holiday_dates", [])

        if current_date in holiday_dates:
            return False, "holiday"

        return True, None

    def _is_time_in_range(
        self,
        current: dt_time,
        start: dt_time,
        end: dt_time
    ) -> bool:
        """
        检查时间是否在指定范围内

        Args:
            current: 当前时间
            start: 开始时间
            end: 结束时间

        Returns:
            bool: 是否在范围内
        """
        if start < end:
            # 正常时间段：如 09:00 - 18:00
            return start <= current <= end
        else:
            # 跨天时间段：如 22:00 - 08:00
            return current >= start or current <= end

    def _is_priority_lower(self, priority: str, threshold: str) -> bool:
        """
        检查优先级是否低于阈值

        Args:
            priority: 当前优先级
            threshold: 阈值优先级

        Returns:
            bool: 是否低于阈值
        """
        priority_order = {"P2": 2, "P1": 1, "P0": 0}
        return priority_order.get(priority, 0) < priority_order.get(threshold, 0)
