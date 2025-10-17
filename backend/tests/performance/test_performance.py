"""
Performance Tests
性能测试套件
"""
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from main import app


class TestAPIPerformance:
    """API性能测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_endpoint_response_time(self, client):
        """测试健康检查端点响应时间"""
        response_times = []

        # 发送100个请求
        for _ in range(100):
            start = time.time()
            response = client.get("/health")
            end = time.time()

            assert response.status_code == 200
            response_times.append((end - start) * 1000)  # 转换为毫秒

        # 分析响应时间
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_time = max(response_times)

        print(f"\n健康检查端点性能:")
        print(f"  平均响应时间: {avg_time:.2f}ms")
        print(f"  P95响应时间: {p95_time:.2f}ms")
        print(f"  最大响应时间: {max_time:.2f}ms")

        # 断言：响应时间应该在合理范围内
        assert avg_time < 100, f"平均响应时间过长: {avg_time:.2f}ms"
        assert p95_time < 200, f"P95响应时间过长: {p95_time:.2f}ms"

    def test_concurrent_health_checks(self, client):
        """测试并发健康检查"""
        concurrent_users = 50
        requests_per_user = 10

        def make_requests(user_id):
            """每个用户发送多个请求"""
            results = []
            for _ in range(requests_per_user):
                start = time.time()
                response = client.get("/health")
                end = time.time()

                results.append({
                    "status_code": response.status_code,
                    "response_time": (end - start) * 1000
                })
            return results

        # 并发执行
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_requests, i) for i in range(concurrent_users)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        end_time = time.time()
        total_time = end_time - start_time

        # 分析结果
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r["status_code"] == 200)
        response_times = [r["response_time"] for r in all_results]

        throughput = total_requests / total_time
        success_rate = (successful_requests / total_requests) * 100
        avg_response_time = statistics.mean(response_times)

        print(f"\n并发性能测试 ({concurrent_users}用户, {requests_per_user}请求/用户):")
        print(f"  总请求数: {total_requests}")
        print(f"  成功请求: {successful_requests}")
        print(f"  成功率: {success_rate:.2f}%")
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  吞吐量: {throughput:.2f} req/s")
        print(f"  平均响应时间: {avg_response_time:.2f}ms")

        # 断言
        assert success_rate >= 95, f"成功率过低: {success_rate:.2f}%"
        assert throughput >= 10, f"吞吐量过低: {throughput:.2f} req/s"


class TestLoadTest:
    """负载测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_sustained_load(self, client):
        """测试持续负载"""
        duration_seconds = 10
        target_rps = 10  # 目标每秒10个请求

        start_time = time.time()
        requests_sent = 0
        response_times = []
        errors = 0

        while time.time() - start_time < duration_seconds:
            request_start = time.time()

            try:
                response = client.get("/health")
                request_end = time.time()

                response_times.append((request_end - request_start) * 1000)

                if response.status_code != 200:
                    errors += 1

                requests_sent += 1

                # 控制请求速率
                time_to_next = (1.0 / target_rps) - (request_end - request_start)
                if time_to_next > 0:
                    time.sleep(time_to_next)

            except Exception as e:
                errors += 1
                print(f"请求错误: {e}")

        actual_duration = time.time() - start_time

        # 分析结果
        actual_rps = requests_sent / actual_duration
        error_rate = (errors / requests_sent) * 100 if requests_sent > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0

        print(f"\n持续负载测试 ({duration_seconds}秒):")
        print(f"  发送请求数: {requests_sent}")
        print(f"  实际RPS: {actual_rps:.2f}")
        print(f"  错误数: {errors}")
        print(f"  错误率: {error_rate:.2f}%")
        print(f"  平均响应时间: {avg_response_time:.2f}ms")

        # 断言
        assert error_rate < 5, f"错误率过高: {error_rate:.2f}%"
        assert actual_rps >= target_rps * 0.8, f"实际RPS低于目标: {actual_rps:.2f} < {target_rps * 0.8}"

    def test_increasing_load(self, client):
        """测试递增负载（ramp-up test）"""
        stages = [
            {"duration": 5, "rps": 5},
            {"duration": 5, "rps": 10},
            {"duration": 5, "rps": 20},
        ]

        results = []

        for stage in stages:
            duration = stage["duration"]
            target_rps = stage["rps"]

            start_time = time.time()
            requests_sent = 0
            response_times = []
            errors = 0

            while time.time() - start_time < duration:
                request_start = time.time()

                try:
                    response = client.get("/health")
                    request_end = time.time()

                    response_times.append((request_end - request_start) * 1000)

                    if response.status_code != 200:
                        errors += 1

                    requests_sent += 1

                    # 控制请求速率
                    time_to_next = (1.0 / target_rps) - (request_end - request_start)
                    if time_to_next > 0:
                        time.sleep(time_to_next)

                except Exception:
                    errors += 1

            actual_duration = time.time() - start_time
            actual_rps = requests_sent / actual_duration
            error_rate = (errors / requests_sent) * 100 if requests_sent > 0 else 0
            avg_response_time = statistics.mean(response_times) if response_times else 0

            results.append({
                "target_rps": target_rps,
                "actual_rps": actual_rps,
                "error_rate": error_rate,
                "avg_response_time": avg_response_time
            })

        print(f"\n递增负载测试:")
        for i, result in enumerate(results):
            print(f"  阶段{i+1} (目标RPS: {result['target_rps']}):")
            print(f"    实际RPS: {result['actual_rps']:.2f}")
            print(f"    错误率: {result['error_rate']:.2f}%")
            print(f"    平均响应时间: {result['avg_response_time']:.2f}ms")

        # 断言：最后阶段的错误率应该可接受
        assert results[-1]["error_rate"] < 10, "高负载下错误率过高"


class TestStressTest:
    """压力测试 - 测试系统极限"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_spike_load(self, client):
        """测试突发负载"""
        # 突然发送大量并发请求
        concurrent_requests = 100

        def send_request(req_id):
            """发送单个请求"""
            start = time.time()
            try:
                response = client.get("/health")
                end = time.time()
                return {
                    "success": response.status_code == 200,
                    "response_time": (end - start) * 1000
                }
            except Exception as e:
                end = time.time()
                return {
                    "success": False,
                    "response_time": (end - start) * 1000,
                    "error": str(e)
                }

        # 并发发送所有请求
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(send_request, i) for i in range(concurrent_requests)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # 分析结果
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        success_rate = (successful / len(results)) * 100
        response_times = [r["response_time"] for r in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        print(f"\n突发负载测试 ({concurrent_requests}并发请求):")
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  成功请求: {successful}")
        print(f"  失败请求: {failed}")
        print(f"  成功率: {success_rate:.2f}%")
        print(f"  平均响应时间: {avg_response_time:.2f}ms")
        print(f"  最大响应时间: {max_response_time:.2f}ms")

        # 断言：即使在突发负载下，系统也应该保持稳定
        assert success_rate >= 80, f"突发负载下成功率过低: {success_rate:.2f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
