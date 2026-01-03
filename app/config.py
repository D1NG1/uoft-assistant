import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# PDF 文件路径配置
PDF_DIR = Path(os.getenv("PDF_DIRECTORY", str(BASE_DIR / "data")))
PDF_FILES: List[str] = os.getenv("PDF_FILES", "MAT235Y.pdf").split(",")

# 数据库配置
DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))

# LLM 配置
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# API 配置
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# 前端 API 基础 URL（自动检测或手动配置）
# 本地开发：http://127.0.0.1:8000
# 生产环境：https://your-domain.com 或留空自动检测
API_BASE_URL = os.getenv("API_BASE_URL", "")

# 安全配置
API_KEY = os.getenv("API_KEY", "dev-secret-key-change-in-production")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))

# 速率限制配置
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
