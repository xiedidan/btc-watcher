"""
API Integration Tests
测试后端API的基本功能
"""
import asyncio
import httpx
import sys
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}

    async def test_health(self) -> bool:
        """测试健康检查端点"""
        print("🔍 Testing health check...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}{API_PREFIX}/system/health")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Health check error: {e}")
                return False

    async def test_register(self, username: str = "testuser", email: str = "test@example.com", password: str = "test123456") -> bool:
        """测试用户注册"""
        print(f"\n🔍 Testing user registration (username: {username})...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{API_PREFIX}/auth/register",
                    json={
                        "username": username,
                        "email": email,
                        "password": password
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Registration successful: {data}")
                    return True
                elif response.status_code == 400:
                    print(f"⚠️  User already exists (this is okay for testing)")
                    return True
                else:
                    print(f"❌ Registration failed: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"❌ Registration error: {e}")
                return False

    async def test_login(self, username: str = "testuser", password: str = "test123456") -> bool:
        """测试用户登录"""
        print(f"\n🔍 Testing user login (username: {username})...")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{API_PREFIX}/auth/token",
                    data={
                        "username": username,
                        "password": password
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    print(f"✅ Login successful, token obtained")
                    return True
                else:
                    print(f"❌ Login failed: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                print(f"❌ Login error: {e}")
                return False

    async def test_get_current_user(self) -> bool:
        """测试获取当前用户信息"""
        print("\n🔍 Testing get current user...")
        if not self.token:
            print("❌ No token available, please login first")
            return False

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{API_PREFIX}/auth/me",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Get current user successful: {data}")
                    return True
                else:
                    print(f"❌ Get current user failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Get current user error: {e}")
                return False

    async def test_capacity(self) -> bool:
        """测试系统容量查询"""
        print("\n🔍 Testing system capacity...")
        if not self.token:
            print("❌ No token available, please login first")
            return False

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{API_PREFIX}/system/capacity",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ System capacity: {data}")
                    print(f"   - Used slots: {data.get('used_slots', 0)}/{data.get('total_slots', 999)}")
                    print(f"   - Utilization: {data.get('utilization_percent', 0):.2f}%")
                    return True
                else:
                    print(f"❌ Get capacity failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Get capacity error: {e}")
                return False

    async def test_create_strategy(self) -> Optional[int]:
        """测试创建策略"""
        print("\n🔍 Testing create strategy...")
        if not self.token:
            print("❌ No token available, please login first")
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{API_PREFIX}/strategies/",
                    headers=self.headers,
                    json={
                        "name": "Test Strategy",
                        "strategy_class": "SampleStrategy",
                        "exchange": "binance",
                        "timeframe": "1h",
                        "pair_whitelist": ["BTC/USDT"],
                        "pair_blacklist": [],
                        "dry_run": True,
                        "dry_run_wallet": 1000,
                        "stake_amount": None,
                        "max_open_trades": 3,
                        "signal_thresholds": {
                            "strong": 0.8,
                            "medium": 0.6,
                            "weak": 0.4
                        }
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    strategy_id = data.get("id")
                    print(f"✅ Strategy created successfully: ID={strategy_id}")
                    return strategy_id
                else:
                    print(f"❌ Create strategy failed: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                print(f"❌ Create strategy error: {e}")
                return None

    async def test_get_strategies(self) -> bool:
        """测试获取策略列表"""
        print("\n🔍 Testing get strategies...")
        if not self.token:
            print("❌ No token available, please login first")
            return False

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{API_PREFIX}/strategies/",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    strategies = data.get("strategies", [])
                    print(f"✅ Found {len(strategies)} strategies")
                    for strategy in strategies[:3]:  # Show first 3
                        print(f"   - {strategy.get('name')} (ID: {strategy.get('id')}, Status: {strategy.get('status')})")
                    return True
                else:
                    print(f"❌ Get strategies failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Get strategies error: {e}")
                return False

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🚀 BTC Watcher API Integration Tests")
        print("=" * 60)

        results = []

        # 1. Health check
        results.append(("Health Check", await self.test_health()))

        # 2. User registration
        results.append(("User Registration", await self.test_register()))

        # 3. User login
        results.append(("User Login", await self.test_login()))

        # 4. Get current user
        results.append(("Get Current User", await self.test_get_current_user()))

        # 5. System capacity
        results.append(("System Capacity", await self.test_capacity()))

        # 6. Create strategy
        strategy_id = await self.test_create_strategy()
        results.append(("Create Strategy", strategy_id is not None))

        # 7. Get strategies
        results.append(("Get Strategies", await self.test_get_strategies()))

        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {name}")

        print(f"\n{'🎉 All tests passed!' if passed == total else '⚠️  Some tests failed'}")
        print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        print("=" * 60)

        return passed == total


async def main():
    """主测试函数"""
    tester = APITester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
