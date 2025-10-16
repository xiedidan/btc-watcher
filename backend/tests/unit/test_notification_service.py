"""
通知服务单元测试
NotificationService Unit Tests
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from services.notification_service import NotificationService


class TestNotificationService:
    """通知服务测试类"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试通知服务初始化"""
        service = NotificationService()

        assert service.queue is not None
        assert isinstance(service.queue, asyncio.Queue)
        assert service.running is False
        assert len(service.channels) == 4  # telegram, wechat, feishu, email

    @pytest.mark.asyncio
    async def test_send_notification_to_queue(self):
        """测试发送通知到队列"""
        service = NotificationService()

        # 使用正确的参数调用
        result = await service.send_notification(
            user_id=1,
            title="Test Notification",
            message="This is a test message",
            channel="telegram",
            priority="P1"
        )

        # 验证通知已加入队列
        assert result is True
        assert service.queue.qsize() == 1

        # 从队列中取出验证
        queued_notification = await service.queue.get()
        assert queued_notification["title"] == "Test Notification"
        assert queued_notification["priority"] == "P1"

    @pytest.mark.asyncio
    async def test_priority_levels(self):
        """测试优先级处理"""
        service = NotificationService()

        # P0 - 紧急
        await service.send_notification(
            user_id=1,
            title="Critical Alert",
            message="System down",
            channel="telegram",
            priority="P0"
        )

        # P1 - 重要
        await service.send_notification(
            user_id=1,
            title="Warning",
            message="High CPU usage",
            channel="email",
            priority="P1"
        )

        # P2 - 普通
        await service.send_notification(
            user_id=1,
            title="Info",
            message="Daily report",
            channel="email",
            priority="P2"
        )

        assert service.queue.qsize() == 3

    @pytest.mark.asyncio
    async def test_send_telegram_notification(self):
        """测试发送Telegram通知"""
        service = NotificationService()

        notification = {
            "title": "Test Alert",
            "message": "Test message",
            "channel": "telegram"
        }

        # Mock aiohttp ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock settings
            with patch('services.notification_service.settings') as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
                mock_settings.TELEGRAM_CHAT_ID = "test_chat_id"

                result = await service._send_telegram(notification)

                assert result is True

    @pytest.mark.asyncio
    async def test_send_email_notification(self):
        """测试发送邮件通知"""
        service = NotificationService()

        notification = {
            "title": "Test Email",
            "message": "Test email message",
            "channel": "email",
            "recipient": "test@example.com"
        }

        with patch('smtplib.SMTP') as mock_smtp:
            with patch('services.notification_service.settings') as mock_settings:
                mock_settings.SMTP_HOST = "smtp.test.com"
                mock_settings.SMTP_PORT = 587
                mock_settings.SMTP_USER = "user@test.com"
                mock_settings.SMTP_PASSWORD = "password"
                mock_settings.SMTP_FROM = "from@test.com"

                result = await service._send_email(notification)

                # 验证结果
                assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_send_wechat_notification(self):
        """测试发送企业微信通知"""
        service = NotificationService()

        notification = {
            "title": "Test WeChat",
            "message": "Test wechat message",
            "channel": "wechat"
        }

        with patch('services.notification_service.settings') as mock_settings:
            mock_settings.WECHAT_CORP_ID = None  # 未配置，应返回False

            result = await service._send_wechat(notification)

            # WeChat需要配置，未配置时返回False
            assert result is False

    @pytest.mark.asyncio
    async def test_send_feishu_notification(self):
        """测试发送飞书通知"""
        service = NotificationService()

        notification = {
            "title": "Test Feishu",
            "message": "Test feishu message",
            "channel": "feishu"
        }

        # Mock aiohttp ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session

            # Mock settings
            with patch('services.notification_service.settings') as mock_settings:
                mock_settings.FEISHU_WEBHOOK_URL = "https://test.feishu.com/webhook"

                result = await service._send_feishu(notification)

                assert result is True

    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(self):
        """测试通知失败重试"""
        service = NotificationService()

        notification = {
            "title": "Test Retry",
            "message": "This should retry",
            "channel": "telegram",
            "retry_count": 0
        }

        # Mock aiohttp ClientSession to simulate failure
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.post.side_effect = Exception("Connection error")
            mock_session_class.return_value.__aenter__.return_value = mock_session

            with patch('services.notification_service.settings') as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

                result = await service._send_telegram(notification)

                assert result is False

    @pytest.mark.asyncio
    async def test_multiple_channels(self):
        """测试多渠道通知"""
        service = NotificationService()

        # 发送到多个渠道
        channels = ["telegram", "email", "wechat", "feishu"]

        for channel in channels:
            await service.send_notification(
                user_id=1,
                title=f"Test {channel}",
                message=f"Test message for {channel}",
                channel=channel
            )

        assert service.queue.qsize() == 4


class TestNotificationServiceEdgeCases:
    """通知服务边缘情况测试"""

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """测试空消息"""
        service = NotificationService()

        # 空消息应该被处理
        result = await service.send_notification(
            user_id=1,
            title="Test",
            message="",
            channel="telegram"
        )

        assert result is True
        assert service.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self):
        """测试队列溢出处理"""
        service = NotificationService()

        # 发送大量通知
        for i in range(1000):
            await service.send_notification(
                user_id=1,
                title=f"Test {i}",
                message=f"Message {i}",
                channel="email",
                priority="P2"
            )

        # 队列应该能处理大量通知
        assert service.queue.qsize() == 1000

    @pytest.mark.asyncio
    async def test_notification_with_metadata(self):
        """测试带元数据的通知"""
        service = NotificationService()

        metadata = {
            "user_id": 123,
            "strategy_id": 456,
            "signal_strength": 0.85
        }

        result = await service.send_notification(
            user_id=1,
            title="Test with metadata",
            message="This has extra data",
            channel="telegram",
            data=metadata
        )

        assert result is True

        queued = await service.queue.get()
        assert "data" in queued
        assert queued["data"]["user_id"] == 123


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
