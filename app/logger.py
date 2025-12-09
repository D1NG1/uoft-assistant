"""
日志配置模块
提供结构化日志功能，支持文件和控制台输出
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from app.config import LOG_LEVEL, LOG_FILE, BASE_DIR


def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    设置并返回一个配置好的 logger

    Args:
        name: Logger 名称，通常使用 __name__
        log_file: 日志文件路径，如果为 None 则使用配置中的默认路径

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    if log_file is None:
        log_file = LOG_FILE

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# 创建默认的应用 logger
app_logger = setup_logger("uoft_assistant")
