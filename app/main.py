import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.rag_service import RAGService
from app.config import API_HOST, API_PORT, ALLOWED_ORIGINS, API_BASE_URL
from app.logger import setup_logger
from app.middleware import security, verify_api_key, check_rate_limit

# 初始化日志
logger = setup_logger(__name__)

# 全局 RAG 服务实例（延迟初始化）
rag_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时后台加载 RAG"""
    global rag_service

    logger.info("创建 RAG 服务实例（延迟加载模式）...")
    rag_service = RAGService(auto_initialize=False)
    logger.info("应用启动完成，准备后台初始化 RAG...")

    # 在后台任务中初始化 RAG，不阻塞应用启动
    async def init_rag():
        try:
            logger.info("开始后台初始化 RAG 系统...")
            await asyncio.to_thread(rag_service.initialize_rag)
            logger.info("RAG 系统后台初始化成功！")
        except Exception as e:
            logger.error(f"RAG 后台初始化失败: {str(e)}", exc_info=True)

    # 启动后台任务
    asyncio.create_task(init_rag())

    yield  # 应用运行

    # 应用关闭时的清理工作（如果需要）
    logger.info("应用关闭...")


# --- FastAPI App 设置 ---
app = FastAPI(
    title="UofT Assistant API",
    description="基于 RAG 的智能课程助手",
    version="1.0.0",
    lifespan=lifespan
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
    # ========================================
    # 🚀 部署到 AWS 时取消下面两行注释：
    # ========================================
    # credentials: HTTPAuthorizationCredentials = Depends(security),
    # _: None = Depends(check_rate_limit)
):
    """
    处理聊天请求

    - **question**: 用户提出的问题（1-2000字符）

    返回 AI 基于课程大纲生成的答案
    """
    # ========================================
    # 🚀 部署到 AWS 时取消下面一行注释：
    # ========================================
    # await verify_api_key(credentials)

    # 检查 RAG 服务是否已初始化
    if rag_service is None:
        logger.warning("RAG 服务尚未创建")
        raise HTTPException(
            status_code=503,
            detail="服务正在启动中，请稍后重试"
        )

    try:
        logger.info(f"收到问题: {request.question[:100]}...")
        answer = rag_service.get_answer(request.question)
        logger.info(f"成功生成答案，长度: {len(answer)} 字符")
        return {"answer": answer}

    except RuntimeError as e:
        error_detail = str(e)
        logger.warning(f"RAG 服务未就绪: {error_detail}")

        # 区分不同的错误情况
        if "正在初始化中" in error_detail:
            raise HTTPException(
                status_code=503,
                detail="RAG 系统正在初始化中，请稍后重试（通常需要 30-60 秒）"
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"RAG 系统暂时不可用: {error_detail}"
            )

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

    返回服务状态信息，包括 RAG 系统状态
    """
    logger.debug("健康检查请求")

    # 检查 RAG 服务状态
    rag_status = "not_initialized"
    rag_error = None

    if rag_service is not None:
        if rag_service.is_ready:
            rag_status = "ready"
        elif rag_service.initialization_error:
            rag_status = "failed"
            rag_error = rag_service.initialization_error
        else:
            rag_status = "initializing"

    return {
        "status": "healthy",
        "service": "uoft-assistant",
        "version": "1.0.0",
        "rag_status": rag_status,
        "rag_error": rag_error
    }


@app.get("/api/config", summary="获取前端配置")
async def get_config(request: Request):
    """
    返回前端配置信息

    自动检测 API 基础 URL，或使用环境变量配置
    """
    # 如果环境变量配置了 API_BASE_URL，使用它
    if API_BASE_URL:
        api_base_url = API_BASE_URL
    else:
        # 否则自动检测（基于请求的 host）
        scheme = request.url.scheme
        host = request.headers.get("host", f"{API_HOST}:{API_PORT}")
        api_base_url = f"{scheme}://{host}"

    logger.debug(f"返回前端配置: api_base_url={api_base_url}")

    return {
        "api_base_url": api_base_url,
        "version": "1.0.0"
    }


# 启动命令: uvicorn app.main:app --reload
