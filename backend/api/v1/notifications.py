"""
Notifications API endpoints
通知管理和配置
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from services.notification_service import NotificationService

router = APIRouter()

# Global service instance (will be injected from main.py)
_notification_service: Optional[NotificationService] = None


def get_notification_service():
    """Get notification service instance"""
    if _notification_service is None:
        raise HTTPException(status_code=500, detail="Notification service not initialized")
    return _notification_service


@router.post("/send")
async def send_notification(
    user_id: int,
    title: str,
    message: str,
    channel: str = "telegram",
    priority: str = "P2",
    notification_type: str = "system",
    notif_service: NotificationService = Depends(get_notification_service)
):
    """发送通知"""
    try:
        success = await notif_service.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            channel=channel,
            priority=priority,
            notification_type=notification_type
        )

        if success:
            return {
                "status": "success",
                "message": "Notification queued successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to queue notification")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_notification(
    channel: str = "telegram",
    notif_service: NotificationService = Depends(get_notification_service)
):
    """测试通知渠道"""
    try:
        success = await notif_service.send_notification(
            user_id=1,  # Admin user
            title="🧪 Test Notification",
            message="This is a test notification from BTC Watcher.",
            channel=channel,
            priority="P2",
            notification_type="system"
        )

        return {
            "status": "success" if success else "failed",
            "channel": channel,
            "message": f"Test notification {'sent' if success else 'failed'}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_notification_statistics(
    hours: int = 24,
    notif_service: NotificationService = Depends(get_notification_service)
):
    """获取通知统计"""
    try:
        stats = await notif_service.get_notification_stats(hours=hours)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels")
async def get_notification_channels():
    """获取可用的通知渠道"""
    return {
        "channels": [
            {
                "id": "telegram",
                "name": "Telegram",
                "description": "Telegram Bot通知",
                "icon": "📱"
            },
            {
                "id": "wechat",
                "name": "企业微信",
                "description": "企业微信群机器人通知",
                "icon": "💬"
            },
            {
                "id": "feishu",
                "name": "飞书",
                "description": "飞书群机器人通知",
                "icon": "🚀"
            },
            {
                "id": "email",
                "name": "邮件",
                "description": "SMTP邮件通知",
                "icon": "📧"
            }
        ]
    }
