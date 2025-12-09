from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag_service import RAGService
from app.config import API_HOST, API_PORT

# --- FastAPI App 设置 ---
app = FastAPI(title="UofT Assistant API")

# 允许跨域 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 全局初始化 RAG 服务
rag_service = RAGService()


# 定义请求数据结构
class QueryRequest(BaseModel):
    question: str


# 定义 API 接口
@app.post("/chat")
async def chat_endpoint(request: QueryRequest):
    """处理聊天请求"""
    try:
        print(f"📩 收到问题: {request.question}")
        answer = rag_service.get_answer(request.question)
        print(f"✅ 回答: {answer[:100]}...")
        return {"answer": answer}
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """根路径重定向到静态页面"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "uoft-assistant"}


# 启动命令: uvicorn app.main:app --reload
