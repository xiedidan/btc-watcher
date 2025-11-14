"""
NotifyHub 功能测试脚本
Test script for NotifyHub functionality
"""
import asyncio
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.session import SessionLocal
from services.notifyhub.core import notify_hub
from models.notification import NotificationChannelConfig, NotificationFrequencyLimit


async def test_notifyhub():
    """测试NotifyHub核心功能"""

    print("=" * 60)
    print("NotifyHub 功能测试")
    print("=" * 60)

    # 1. 启动NotifyHub
    print("\n[1/7] 启动NotifyHub...")
    try:
        await notify_hub.start()
        print("✅ NotifyHub启动成功")
    except Exception as e:
        print(f"❌ NotifyHub启动失败: {e}")
        return

    # 2. 检查健康状态
    print("\n[2/7] 检查NotifyHub健康状态...")
    try:
        status = await notify_hub.get_queue_status()
        print(f"✅ NotifyHub运行状态: {status}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")

    # 3. 创建测试数据库会话
    print("\n[3/7] 初始化数据库连接...")
    async with SessionLocal() as db:
        try:
            # 4. 创建测试通知渠道配置（Telegram示例）
            print("\n[4/7] 创建测试通知渠道配置...")

            # 检查是否已存在测试配置
            from sqlalchemy import select
            result = await db.execute(
                select(NotificationChannelConfig).where(
                    NotificationChannelConfig.user_id == 1,
                    NotificationChannelConfig.channel_type == "telegram"
                ).limit(1)
            )
            existing_config = result.scalar_one_or_none()

            if not existing_config:
                test_channel = NotificationChannelConfig(
                    user_id=1,
                    channel_type="telegram",
                    channel_name="测试Telegram渠道",
                    enabled=True,
                    priority=1,
                    supported_priorities=["P2", "P1", "P0"],
                    config={
                        "bot_token": "test_bot_token",
                        "chat_id": "test_chat_id"
                    },
                    rate_limit_enabled=False  # 测试时禁用频率限制
                )
                db.add(test_channel)
                await db.commit()
                print("✅ 测试通知渠道配置已创建")
            else:
                print("ℹ️  测试通知渠道配置已存在")

            # 5. 创建测试频率限制配置
            print("\n[5/7] 创建测试频率限制配置...")
            result = await db.execute(
                select(NotificationFrequencyLimit).where(
                    NotificationFrequencyLimit.user_id == 1
                ).limit(1)
            )
            existing_freq = result.scalar_one_or_none()

            if not existing_freq:
                test_freq = NotificationFrequencyLimit(
                    user_id=1,
                    p2_min_interval=0,
                    p1_min_interval=5,  # 测试时设置为5秒
                    p0_batch_interval=10,  # 测试时设置为10秒
                    p0_batch_enabled=True,
                    p0_batch_max_size=5,
                    enabled=True
                )
                db.add(test_freq)
                await db.commit()
                print("✅ 测试频率限制配置已创建")
            else:
                print("ℹ️  测试频率限制配置已存在")

            # 6. 发送测试通知
            print("\n[6/7] 发送测试通知...")

            # 测试P2优先级（最高）
            print("\n  发送P2通知（最高优先级）...")
            success = await notify_hub.notify(
                user_id=1,
                title="🔴 P2测试通知",
                message="这是一条P2（最高优先级）测试通知，应该立即发送。",
                notification_type="info",
                priority="P2",
                metadata={"test": True, "priority_level": "high"}
            )
            print(f"  {'✅' if success else '❌'} P2通知已{'加入队列' if success else '失败'}")

            # 等待一会儿让通知处理
            await asyncio.sleep(2)

            # 测试P1优先级（中等）
            print("\n  发送P1通知（中等优先级）...")
            success = await notify_hub.notify(
                user_id=1,
                title="🟠 P1测试通知",
                message="这是一条P1（中等优先级）测试通知，会进行频率控制。",
                notification_type="info",
                priority="P1",
                metadata={"test": True, "priority_level": "medium"}
            )
            print(f"  {'✅' if success else '❌'} P1通知已{'加入队列' if success else '失败'}")

            await asyncio.sleep(2)

            # 测试P0优先级（最低，批量发送）
            print("\n  发送多条P0通知（最低优先级，将批量发送）...")
            for i in range(3):
                success = await notify_hub.notify(
                    user_id=1,
                    title=f"⚪ P0测试通知 #{i+1}",
                    message=f"这是第{i+1}条P0（最低优先级）测试通知，将被批量合并发送。",
                    notification_type="info",
                    priority="P0",
                    metadata={"test": True, "priority_level": "low", "batch_id": i+1}
                )
                print(f"  {'✅' if success else '❌'} P0通知#{i+1}已{'加入队列' if success else '失败'}")

            await asyncio.sleep(1)

            # 7. 检查队列状态
            print("\n[7/7] 检查队列状态...")
            status = await notify_hub.get_queue_status()
            print(f"  队列大小: {status['queue_size']}")
            print(f"  批量队列数: {status['batch_queues']}")
            print(f"  批量通知总数: {status['total_batched_notifications']}")

            # 等待通知处理完成
            print("\n等待5秒让通知处理完成...")
            await asyncio.sleep(5)

            # 再次检查队列状态
            status = await notify_hub.get_queue_status()
            print(f"\n处理后队列状态:")
            print(f"  队列大小: {status['queue_size']}")
            print(f"  批量队列数: {status['batch_queues']}")
            print(f"  批量通知总数: {status['total_batched_notifications']}")

        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()

    # 停止NotifyHub
    print("\n停止NotifyHub...")
    try:
        await notify_hub.stop()
        print("✅ NotifyHub已停止")
    except Exception as e:
        print(f"❌ NotifyHub停止失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n注意事项：")
    print("1. 由于使用了测试bot_token和chat_id，实际发送会失败（这是正常的）")
    print("2. 但通知应该已经被正确路由和记录到notification_history表")
    print("3. 可以通过以下SQL查看通知历史：")
    print("   SELECT * FROM notification_history ORDER BY created_at DESC LIMIT 10;")
    print("\n要测试真实发送，请：")
    print("1. 配置真实的Telegram/Discord/飞书渠道")
    print("2. 使用API: POST /api/v1/notify/send")


async def test_channels():
    """测试各个通知渠道"""
    print("\n" + "=" * 60)
    print("测试通知渠道适配器")
    print("=" * 60)

    # 测试Telegram渠道
    print("\n测试Telegram渠道...")
    from services.notifyhub.channels import TelegramChannel
    try:
        telegram = TelegramChannel({
            "bot_token": "test_token",
            "chat_id": "test_chat_id"
        })
        print("✅ Telegram渠道实例创建成功")
        print(f"   渠道类型: {telegram.channel_type}")
    except Exception as e:
        print(f"❌ Telegram渠道创建失败: {e}")

    # 测试Discord渠道
    print("\n测试Discord渠道...")
    from services.notifyhub.channels import DiscordChannel
    try:
        discord = DiscordChannel({
            "webhook_url": "https://discord.com/api/webhooks/test/test"
        })
        print("✅ Discord渠道实例创建成功")
        print(f"   渠道类型: {discord.channel_type}")
    except Exception as e:
        print(f"❌ Discord渠道创建失败: {e}")

    # 测试飞书渠道
    print("\n测试飞书渠道...")
    from services.notifyhub.channels import FeishuChannel
    try:
        feishu = FeishuChannel({
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test"
        })
        print("✅ 飞书渠道实例创建成功")
        print(f"   渠道类型: {feishu.channel_type}")
    except Exception as e:
        print(f"❌ 飞书渠道创建失败: {e}")


async def test_frequency_controller():
    """测试频率控制器"""
    print("\n" + "=" * 60)
    print("测试频率控制器")
    print("=" * 60)

    from services.notifyhub.frequency_controller import FrequencyController

    controller = FrequencyController()

    # 测试P2（应该总是允许）
    print("\n测试P2优先级（应该总是允许）...")
    for i in range(3):
        should_send, reason = await controller.should_send(1, "telegram", "P2", None)
        print(f"  第{i+1}次: {'✅ 允许' if should_send else f'❌ 拒绝 ({reason})'}")

    # 测试P1（有频率限制）
    print("\n测试P1优先级（有频率限制，60秒间隔）...")
    config = {"p1_min_interval": 60, "enabled": True}
    for i in range(3):
        should_send, reason = await controller.should_send(1, "telegram", "P1", config)
        status = '✅ 允许' if should_send else f'❌ 拒绝 ({reason})'
        print(f"  第{i+1}次: {status}")
        await asyncio.sleep(1)

    # 测试P0（批量发送）
    print("\n测试P0优先级（批量发送模式）...")
    config = {"p0_batch_enabled": True, "enabled": True}
    for i in range(3):
        should_send, reason = await controller.should_send(1, "telegram", "P0", config)
        if not should_send and reason == "batched":
            print(f"  第{i+1}次: ℹ️  加入批量队列")
            controller.add_to_batch(1, "telegram", {"title": f"测试通知{i+1}"})
        else:
            print(f"  第{i+1}次: {'✅ 允许' if should_send else f'❌ 拒绝 ({reason})'}")

    # 查看批量队列
    batch_queue = controller.get_batch_queue(1, "telegram")
    print(f"\n批量队列大小: {len(batch_queue)}")

    # 获取统计
    stats = controller.get_stats()
    print(f"\n频率控制器统计:")
    print(f"  活跃渠道数: {stats['active_channels']}")
    print(f"  批量队列数: {stats['batch_queues']}")
    print(f"  批量通知总数: {stats['total_batched_notifications']}")


async def test_time_rule_manager():
    """测试时间规则管理器"""
    print("\n" + "=" * 60)
    print("测试时间规则管理器")
    print("=" * 60)

    from services.notifyhub.time_rule_manager import TimeRuleManager
    from datetime import datetime

    manager = TimeRuleManager()

    # 测试勿扰时段
    print("\n测试勿扰时段规则...")
    time_rule = {
        "enabled": True,
        "quiet_hours_enabled": True,
        "quiet_start_time": "22:00",
        "quiet_end_time": "08:00",
        "quiet_priority_filter": "P2"
    }

    current_hour = datetime.now().hour
    print(f"当前时间: {datetime.now().strftime('%H:%M')}")

    for priority in ["P2", "P1", "P0"]:
        should_send, reason = await manager.should_send_at_current_time(time_rule, priority)
        status = f"✅ 允许发送" if should_send else f"❌ 拒绝发送 ({reason})"
        print(f"  {priority}: {status}")

    # 测试周末模式
    print("\n测试周末模式规则...")
    time_rule = {
        "enabled": True,
        "weekend_mode_enabled": True,
        "weekend_downgrade_p1_to_p0": True
    }

    is_weekend = datetime.now().isoweekday() in [6, 7]
    print(f"今天是{'周末' if is_weekend else '工作日'}")

    for priority in ["P2", "P1", "P0"]:
        should_send, reason = await manager.should_send_at_current_time(time_rule, priority)
        status = f"✅ 允许发送" if should_send else f"❌ 拒绝发送 ({reason})"
        print(f"  {priority}: {status}")


async def main():
    """主测试函数"""
    try:
        # 运行所有测试
        await test_channels()
        await test_frequency_controller()
        await test_time_rule_manager()
        await test_notifyhub()

        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
