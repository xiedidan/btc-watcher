"""
数据模型单元测试
Data Models Unit Tests
"""
import pytest
from datetime import datetime
from models.user import User
from models.strategy import Strategy
from models.signal import Signal
from models.notification import Notification


class TestUserModel:
    """用户模型测试"""

    def test_user_creation(self, db_session):
        """测试创建用户"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_here",
            is_active=True,
            is_superuser=False
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_unique_username(self, db_session):
        """测试用户名唯一性"""
        user1 = User(
            username="duplicate",
            email="user1@example.com",
            hashed_password="hash1"
        )
        user2 = User(
            username="duplicate",
            email="user2@example.com",
            hashed_password="hash2"
        )

        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_user_unique_email(self, db_session):
        """测试邮箱唯一性"""
        user1 = User(
            username="user1",
            email="duplicate@example.com",
            hashed_password="hash1"
        )
        user2 = User(
            username="user2",
            email="duplicate@example.com",
            hashed_password="hash2"
        )

        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)
        with pytest.raises(Exception):
            db_session.commit()


class TestStrategyModel:
    """策略模型测试"""

    def test_strategy_creation(self, db_session, sample_user):
        """测试创建策略"""
        strategy = Strategy(
            user_id=sample_user.id,
            name="Test Strategy",
            strategy_class="SampleStrategy",
            exchange="binance",
            timeframe="1h",
            pair_whitelist=["BTC/USDT", "ETH/USDT"],
            pair_blacklist=[],
            dry_run=True,
            dry_run_wallet=1000.0,
            max_open_trades=3,
            status="stopped",
            signal_thresholds={"strong": 0.8, "medium": 0.6, "weak": 0.4}
        )

        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        assert strategy.id is not None
        assert strategy.user_id == sample_user.id
        assert strategy.name == "Test Strategy"
        assert strategy.status == "stopped"
        assert len(strategy.pair_whitelist) == 2

    def test_strategy_default_status(self, db_session, sample_user):
        """测试策略默认状态"""
        strategy = Strategy(
            user_id=sample_user.id,
            name="Default Status Strategy",
            strategy_class="SampleStrategy",
            exchange="binance",
            timeframe="1h",
            pair_whitelist=["BTC/USDT"]
        )

        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        assert strategy.status == "stopped"

    def test_strategy_user_relationship(self, db_session, sample_user):
        """测试策略与用户关系"""
        strategy = Strategy(
            user_id=sample_user.id,
            name="Relationship Test",
            strategy_class="SampleStrategy",
            exchange="binance",
            timeframe="1h",
            pair_whitelist=["BTC/USDT"]
        )

        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        # 通过关系访问用户
        assert strategy.user.id == sample_user.id
        assert strategy.user.username == sample_user.username


class TestSignalModel:
    """信号模型测试"""

    def test_signal_creation(self, db_session, sample_strategy):
        """测试创建信号"""
        signal = Signal(
            strategy_id=sample_strategy.id,
            pair="BTC/USDT",
            action="buy",
            signal_strength=0.85,
            price=50000.0,
            volume=1.5,
            timestamp=datetime.utcnow(),
            metadata={"indicator": "RSI", "value": 30}
        )

        db_session.add(signal)
        db_session.commit()
        db_session.refresh(signal)

        assert signal.id is not None
        assert signal.strategy_id == sample_strategy.id
        assert signal.pair == "BTC/USDT"
        assert signal.action == "buy"
        assert signal.signal_strength == 0.85

    def test_signal_strategy_relationship(self, db_session, sample_strategy):
        """测试信号与策略关系"""
        signal = Signal(
            strategy_id=sample_strategy.id,
            pair="ETH/USDT",
            action="sell",
            signal_strength=0.75,
            price=3000.0,
            timestamp=datetime.utcnow()
        )

        db_session.add(signal)
        db_session.commit()
        db_session.refresh(signal)

        # 通过关系访问策略
        assert signal.strategy.id == sample_strategy.id
        assert signal.strategy.name == sample_strategy.name


class TestNotificationModel:
    """通知模型测试"""

    def test_notification_creation(self, db_session, sample_user):
        """测试创建通知"""
        notification = Notification(
            user_id=sample_user.id,
            type="alert",
            title="High CPU Usage",
            message="CPU usage is above 90%",
            priority="P1",
            channel="telegram",
            status="pending"
        )

        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        assert notification.id is not None
        assert notification.user_id == sample_user.id
        assert notification.type == "alert"
        assert notification.priority == "P1"

    def test_notification_default_status(self, db_session, sample_user):
        """测试通知默认状态"""
        notification = Notification(
            user_id=sample_user.id,
            type="info",
            title="Test Notification",
            message="Test message",
            channel="email"
        )

        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        assert notification.status == "pending"

    def test_notification_user_relationship(self, db_session, sample_user):
        """测试通知与用户关系"""
        notification = Notification(
            user_id=sample_user.id,
            type="warning",
            title="Test Warning",
            message="This is a warning",
            channel="telegram"
        )

        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        # 通过关系访问用户
        assert notification.user.id == sample_user.id
        assert notification.user.username == sample_user.username


class TestModelTimestamps:
    """模型时间戳测试"""

    def test_user_timestamps(self, db_session):
        """测试用户时间戳"""
        user = User(
            username="timestamp_test",
            email="timestamp@example.com",
            hashed_password="hash"
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at <= user.updated_at

    def test_strategy_timestamps(self, db_session, sample_user):
        """测试策略时间戳"""
        strategy = Strategy(
            user_id=sample_user.id,
            name="Timestamp Test",
            strategy_class="SampleStrategy",
            exchange="binance",
            timeframe="1h",
            pair_whitelist=["BTC/USDT"]
        )

        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)

        assert strategy.created_at is not None
        assert strategy.updated_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
