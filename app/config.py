import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# PDF 文件路径配置
PDF_DIR = BASE_DIR / "data"
PDF_FILES = [
    "MAT235Y12025-26Syllabus.pdf",
    # 添加更多 PDF 文件名到这里
]

# 数据库配置
DB_PATH = str(BASE_DIR / "chroma_db")

# LLM 配置
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# API 配置
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
