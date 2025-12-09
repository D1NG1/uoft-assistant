"""
中间件模块
包含 API 认证、速率限制等中间件
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from app.config import API_KEY, RATE_LIMIT_PER_MINUTE
from app.logger import setup_logger

logger = setup_logger(__name__)

# API 密钥认证
security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
    """
    验证 API 密钥

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        是否通过验证

    Raises:
        HTTPException: 认证失败时抛出 401 错误
    """
    if not credentials:
        logger.warning("请求缺少认证凭证")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != API_KEY:
        logger.warning(f"无效的 API 密钥尝试")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


# 速率限制器
class RateLimiter:
    """简单的内存速率限制器"""

    def __init__(self, max_requests: int = RATE_LIMIT_PER_MINUTE, window_seconds: int = 60):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        """
        检查客户端是否被允许发送请求

        Args:
            client_id: 客户端标识（通常是 IP 地址）

        Returns:
            是否允许请求
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        with self.lock:
            # 清理过期的请求记录
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff
            ]

            # 检查是否超过限制
            if len(self.requests[client_id]) >= self.max_requests:
                logger.warning(f"客户端 {client_id} 超过速率限制")
                return False

            # 记录当前请求
            self.requests[client_id].append(now)
            return True


# 创建全局速率限制器实例
rate_limiter = RateLimiter(max_requests=RATE_LIMIT_PER_MINUTE, window_seconds=60)


async def check_rate_limit(request: Request) -> None:
    """
    检查速率限制中间件

    Args:
        request: FastAPI 请求对象

    Raises:
        HTTPException: 超过速率限制时抛出 429 错误
    """
    client_ip = request.client.host if request.client else "unknown"

    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"速率限制: 客户端 {client_ip} 请求过于频繁")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_PER_MINUTE} requests per minute."
        )

    logger.debug(f"速率检查通过: {client_ip}")
