"""
Authentication Integration Tests
认证流程集成测试
"""
import pytest
from httpx import AsyncClient


class TestAuthenticationFlow:
    """认证流程集成测试"""

    def test_user_registration_flow(self, client, test_db):
        """测试用户注册流程"""
        # 1. 注册新用户
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepass123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data

        # 2. 尝试重复注册（应该失败）
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "another@example.com",
                "password": "securepass123"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_flow(self, client, test_user):
        """测试登录流程"""
        # 1. 使用正确的凭证登录
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": test_user["user"].username,
                "password": test_user["password"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == test_user["user"].username

        # 2. 使用错误的密码登录（应该失败）
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": test_user["user"].username,
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401

    def test_get_current_user(self, client, test_user):
        """测试获取当前用户信息"""
        # 1. 先登录获取token
        login_response = client.post(
            "/api/v1/auth/token",
            data={
                "username": test_user["user"].username,
                "password": test_user["password"]
            }
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 2. 使用token获取用户信息
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user["user"].username
        assert data["email"] == test_user["user"].email

        # 3. 不带token访问（应该失败）
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_invalid_token(self, client):
        """测试无效token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401

    def test_complete_auth_workflow(self, client, test_db):
        """测试完整的认证工作流"""
        # 1. 注册
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "workflowuser",
                "email": "workflow@example.com",
                "password": "workflow123"
            }
        )

        assert register_response.status_code == 201
        user_id = register_response.json()["id"]

        # 2. 登录
        login_response = client.post(
            "/api/v1/auth/token",
            data={
                "username": "workflowuser",
                "password": "workflow123"
            }
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 3. 访问受保护的资源
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert me_response.status_code == 200
        assert me_response.json()["id"] == user_id


class TestAuthenticationValidation:
    """认证数据验证测试"""

    def test_register_invalid_email(self, client, test_db):
        """测试无效邮箱注册"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "password123"
            }
        )

        assert response.status_code == 422

    def test_register_short_password(self, client, test_db):
        """测试过短密码"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123"  # 少于6个字符
            }
        )

        assert response.status_code == 422

    def test_register_missing_fields(self, client, test_db):
        """测试缺少必需字段"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser"
                # 缺少email和password
            }
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
