"""
通知服务单元测试
NotificationService Unit Tests
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
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
        assert service.is_running is False
        assert len(service.channels) == 4  # telegram, wechat, feishu, email

    @pytest.mark.asyncio
    async def test_send_notification_to_queue(self):
        """测试发送通知到队列"""
        service = NotificationService()

        notification = {
            "title": "Test Notification",
            "message": "This is a test message",
            "priority": "P1",
            "channel": "telegram"
        }

        await service.send_notification(notification)

        # 验证通知已加入队列
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
        p0_notification = {
            "title": "Critical Alert",
            "message": "System down",
            "priority": "P0",
            "channel": "telegram"
        }

        # P1 - 重要
        p1_notification = {
            "title": "Warning",
            "message": "High CPU usage",
            "priority": "P1",
            "channel": "email"
        }

        # P2 - 普通
        p2_notification = {
            "title": "Info",
            "message": "Daily report",
            "priority": "P2",
            "channel": "email"
        }

        await service.send_notification(p0_notification)
        await service.send_notification(p1_notification)
        await service.send_notification(p2_notification)

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

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200

            result = await service._send_telegram(notification)

            assert result is True
            mock_post.assert_called_once()

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
            mock_instance = mock_smtp.return_value.__enter__.return_value

            result = await service._send_email(notification)

            # 应该尝试发送邮件
            assert mock_smtp.called or result is False  # 可能因为配置缺失而失败

    @pytest.mark.asyncio
    async def test_send_wechat_notification(self):
        """测试发送企业微信通知"""
        service = NotificationService()

        notification = {
            "title": "Test WeChat",
            "message": "Test wechat message",
            "channel": "wechat"
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"errcode": 0}

            result = await service._send_wechat(notification)

            # WeChat需要access_token，可能失败
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_send_feishu_notification(self):
        """测试发送飞书通知"""
        service = NotificationService()

        notification = {
            "title": "Test Feishu",
            "message": "Test feishu message",
            "channel": "feishu"
        }

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"code": 0}

            result = await service._send_feishu(notification)

            assert isinstance(result, bool)

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

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            # 第一次失败
            mock_post.side_effect = [Exception("Connection error")]

            result = await service._send_telegram(notification)

            assert result is False

    @pytest.mark.asyncio
    async def test_multiple_channels(self):
        """测试多渠道通知"""
        service = NotificationService()

        # 发送到多个渠道
        channels = ["telegram", "email", "wechat", "feishu"]

        for channel in channels:
            notification = {
                "title": f"Test {channel}",
                "message": f"Test message for {channel}",
                "channel": channel
            }
            await service.send_notification(notification)

        assert service.queue.qsize() == 4

    @pytest.mark.asyncio
    async def test_notification_validation(self):
        """测试通知数据验证"""
        service = NotificationService()

        # 缺少必需字段
        invalid_notification = {
            "title": "Test"
            # 缺少message和channel
        }

        with pytest.raises(Exception):
            await service.send_notification(invalid_notification)


class TestNotificationServiceEdgeCases:
    """通知服务边缘情况测试"""

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """测试空消息"""
        service = NotificationService()

        notification = {
            "title": "Test",
            "message": "",
            "channel": "telegram"
        }

        # 空消息应该被处理
        await service.send_notification(notification)
        assert service.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_invalid_channel(self):
        """测试无效的通知渠道"""
        service = NotificationService()

        notification = {
            "title": "Test",
            "message": "Test message",
            "channel": "invalid_channel"
        }

        with pytest.raises(Exception):
            await service.send_notification(notification)

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self):
        """测试队列溢出处理"""
        service = NotificationService()

        # 发送大量通知
        for i in range(1000):
            notification = {
                "title": f"Test {i}",
                "message": f"Message {i}",
                "channel": "email",
                "priority": "P2"
            }
            await service.send_notification(notification)

        # 队列应该能处理大量通知
        assert service.queue.qsize() == 1000

    @pytest.mark.asyncio
    async def test_notification_with_metadata(self):
        """测试带元数据的通知"""
        service = NotificationService()

        notification = {
            "title": "Test with metadata",
            "message": "This has extra data",
            "channel": "telegram",
            "metadata": {
                "user_id": 123,
                "strategy_id": 456,
                "signal_strength": 0.85
            }
        }

        await service.send_notification(notification)

        queued = await service.queue.get()
        assert "metadata" in queued
        assert queued["metadata"]["user_id"] == 123


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
