import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.config import PDF_DIR, PDF_FILES, DB_PATH, LLM_MODEL, EMBED_MODEL


class RAGService:
    """RAG (Retrieval-Augmented Generation) 服务类"""

    def __init__(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None
        self.initialize_rag()

    def initialize_rag(self):
        """初始化 RAG 引擎"""
        print("🚀 [Backend] 正在初始化 RAG 引擎...")

        # 1. 模型初始化
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        llm = ChatOllama(model=LLM_MODEL)

        # 2. 检查并建立向量库
        if not os.path.exists(DB_PATH):
            print(f"📄 [Backend] 未发现数据库，正在处理 PDF 文件...")
            self._load_pdfs_to_vector_store(embeddings)
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

    def _load_pdfs_to_vector_store(self, embeddings):
        """加载所有 PDF 文件到向量数据库"""
        all_splits = []

        for pdf_file in PDF_FILES:
            pdf_path = PDF_DIR / pdf_file
            if not pdf_path.exists():
                print(f"⚠️ [Backend] 警告: 找不到文件 {pdf_path}")
                continue

            print(f"📄 [Backend] 处理 PDF: {pdf_file}...")
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(docs)
            all_splits.extend(splits)

        if not all_splits:
            raise FileNotFoundError(f"未找到任何 PDF 文件在 {PDF_DIR}")

        print(f"📊 [Backend] 共处理 {len(all_splits)} 个文档片段")
        self.vector_store = Chroma.from_documents(
            documents=all_splits,
            embedding_function=embeddings,
            persist_directory=DB_PATH
        )
        print("💾 [Backend] 向量库建立完成！")

    def get_answer(self, question: str) -> str:
        """获取问题的答案"""
        if not self.chain:
            return "System not initialized."
        return self.chain.invoke(question)
