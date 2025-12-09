"""
API 端点集成测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.config import API_KEY


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """创建认证头"""
    return {"Authorization": f"Bearer {API_KEY}"}


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "uoft-assistant"
        assert "version" in data


class TestChatEndpoint:
    """聊天端点测试"""

    def test_chat_without_auth(self, client):
        """测试无认证请求"""
        response = client.post(
            "/chat",
            json={"question": "What is the course about?"}
        )
        assert response.status_code == 401

    def test_chat_with_invalid_auth(self, client):
        """测试无效认证"""
        response = client.post(
            "/chat",
            json={"question": "What is the course about?"},
            headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 401

    @patch('app.main.rag_service.get_answer')
    def test_chat_success(self, mock_get_answer, client, auth_headers):
        """测试成功的聊天请求"""
        # 模拟 RAG 服务返回
        mock_answer = "This course is about multivariable calculus."
        mock_get_answer.return_value = mock_answer

        response = client.post(
            "/chat",
            json={"question": "What is the course about?"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == mock_answer

    def test_chat_with_empty_question(self, client, auth_headers):
        """测试空问题"""
        response = client.post(
            "/chat",
            json={"question": ""},
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    def test_chat_with_long_question(self, client, auth_headers):
        """测试超长问题"""
        long_question = "a" * 3000  # 超过 2000 字符限制
        response = client.post(
            "/chat",
            json={"question": long_question},
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    @patch('app.main.rag_service.get_answer')
    def test_chat_service_error(self, mock_get_answer, client, auth_headers):
        """测试服务错误"""
        # 模拟 RAG 服务抛出异常
        mock_get_answer.side_effect = RuntimeError("Service not initialized")

        response = client.post(
            "/chat",
            json={"question": "What is the course about?"},
            headers=auth_headers
        )

        assert response.status_code == 503
        assert "不可用" in response.json()["detail"]


class TestRateLimiting:
    """速率限制测试"""

    @patch('app.main.rag_service.get_answer')
    def test_rate_limiting(self, mock_get_answer, client, auth_headers):
        """测试速率限制"""
        mock_get_answer.return_value = "Test answer"

        # 发送大量请求
        for i in range(15):  # 超过限制（默认 10/分钟）
            response = client.post(
                "/chat",
                json={"question": f"Question {i}"},
                headers=auth_headers
            )

            if i < 10:
                # 前 10 个应该成功
                assert response.status_code == 200
            else:
                # 后续应该被限制
                assert response.status_code == 429
