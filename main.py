import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# --- 配置 ---
PDF_PATH = "data/MAT235Y12025-26Syllabus.pdf"  # 请确保文件名和路径正确
DB_PATH = "./chroma_db_web"     # 这里换个新名字，防止和之前的冲突
LLM_MODEL = "llama3"
EMBED_MODEL = "nomic-embed-text" # 记得一定要用这个！

# --- RAG 引擎类 (封装逻辑) ---
class RAGService:
    def __init__(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self.initialize_rag()

    def initialize_rag(self):
        print("🚀 [Backend] 正在初始化 RAG 引擎...")
        
        # 1. 模型初始化
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        llm = ChatOllama(model=LLM_MODEL)

        # 2. 检查并建立向量库
        if not os.path.exists(DB_PATH):
            print(f"📄 [Backend] 未发现数据库，正在处理 PDF: {PDF_PATH}...")
            if not os.path.exists(PDF_PATH):
                raise FileNotFoundError(f"找不到 PDF 文件: {PDF_PATH}")
            
            loader = PyPDFLoader(PDF_PATH)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            
            self.vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=DB_PATH
            )
            print("💾 [Backend] 向量库建立完成！")
        else:
            print("💾 [Backend] 加载已有向量库...")
            self.vector_store = Chroma(
                persist_directory=DB_PATH,
                embedding_function=embeddings
            )

        # 3. 设置检索器
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})

        # 4. 设置 Prompt 和 Chain
        template = """
        You are an intelligent teaching assistant. Answer the student's question based ONLY on the context below.
        If the answer is not in the context, say "I cannot find this information in the syllabus."
        
        Context:
        {context}
        
        Question:
        {question}
        """
        prompt = ChatPromptTemplate.from_template(template)
        
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        print("✅ [Backend] 系统就绪！")

    def get_answer(self, question: str):
        if not self.chain:
            return "System not initialized."
        return self.chain.invoke(question)

# --- FastAPI App 设置 ---
app = FastAPI()

# 允许跨域 (CORS)，这样你的 HTML 文件才能直接访问这个 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局初始化 RAG 服务 (启动时只运行一次)
rag_service = RAGService()

# 定义请求数据结构
class QueryRequest(BaseModel):
    question: str

# 定义 API 接口
@app.post("/chat")
async def chat_endpoint(request: QueryRequest):
    try:
        print(f"📩 收到问题: {request.question}")
        answer = rag_service.get_answer(request.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 启动命令: uvicorn main:app --reload