from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.rag_service import RAGService
from app.config import API_HOST, API_PORT, ALLOWED_ORIGINS
from app.logger import setup_logger
from app.middleware import security, verify_api_key, check_rate_limit

# 初始化日志
logger = setup_logger(__name__)

# --- FastAPI App 设置 ---
app = FastAPI(
    title="UofT Assistant API",
    description="基于 RAG 的智能课程助手",
    version="1.0.0"
)

# 允许跨域 (CORS)
logger.info(f"配置 CORS，允许的来源: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 全局初始化 RAG 服务
logger.info("初始化 RAG 服务...")
rag_service = RAGService()
logger.info("应用启动完成")


# --- 全局异常处理器 ---
@app.exception_handler(Exception)
async def global_exception_handler(exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="服务器内部错误，请稍后重试"
    )


# --- 定义请求/响应数据结构 ---
class QueryRequest(BaseModel):
    """聊天请求模型"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the grading scheme for this course?"
            }
        }


class QueryResponse(BaseModel):
    """聊天响应模型"""
    answer: str = Field(..., description="AI 生成的答案")


# --- API 接口 ---
@app.post("/chat", response_model=QueryResponse, summary="聊天接口")
async def chat_endpoint(
    request: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _: None = Depends(check_rate_limit)
):
    """
    处理聊天请求

    - **question**: 用户提出的问题（1-2000字符）

    返回 AI 基于课程大纲生成的答案
    """
    await verify_api_key(credentials)

    try:
        logger.info(f"收到问题: {request.question[:100]}...")
        answer = rag_service.get_answer(request.question)
        logger.info(f"成功生成答案，长度: {len(answer)} 字符")
        return {"answer": answer}

    except RuntimeError as e:
        logger.error(f"RAG 服务错误: {str(e)}")
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="处理请求时发生错误")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """根路径重定向到静态页面"""
    return RedirectResponse(url="/static/index.html")


@app.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    返回服务状态信息
    """
    logger.debug("健康检查请求")
    return {
        "status": "healthy",
        "service": "uoft-assistant",
        "version": "1.0.0"
    }


# 启动命令: uvicorn app.main:app --reload
