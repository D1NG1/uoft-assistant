import os
from pathlib import Path
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

from app.config import PDF_DIR, PDF_FILES, DB_PATH, LLM_MODEL, EMBED_MODEL
from app.logger import setup_logger

# 初始化日志
logger = setup_logger(__name__)


class RAGService:
    """RAG (Retrieval-Augmented Generation) 服务类"""

    def __init__(self):
        self.vector_store: Optional[Chroma] = None
        self.retriever = None
        self.chain = None
        self.initialize_rag()

    def initialize_rag(self) -> None:
        """初始化 RAG 引擎"""
        logger.info("正在初始化 RAG 引擎...")

        try:
            # 1. 模型初始化
            logger.info(f"初始化嵌入模型: {EMBED_MODEL}")
            embeddings = OllamaEmbeddings(model=EMBED_MODEL)

            logger.info(f"初始化 LLM 模型: {LLM_MODEL}")
            llm = ChatOllama(model=LLM_MODEL)

            # 2. 检查并建立向量库
            if not os.path.exists(DB_PATH):
                logger.info("未发现数据库，正在处理 PDF 文件...")
                self._load_pdfs_to_vector_store(embeddings)
            else:
                logger.info(f"从 {DB_PATH} 加载已有向量库...")
                self.vector_store = Chroma(
                    persist_directory=DB_PATH,
                    embedding_function=embeddings
                )

            # 3. 设置检索器
            logger.info("配置检索器 (K=5)...")
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
            logger.info("RAG 系统初始化完成，系统就绪！")

        except Exception as e:
            logger.error(f"RAG 初始化失败: {str(e)}", exc_info=True)
            raise

    def _load_pdfs_to_vector_store(self, embeddings: OllamaEmbeddings) -> None:
        """加载所有 PDF 文件到向量数据库

        Args:
            embeddings: Ollama 嵌入模型实例

        Raises:
            FileNotFoundError: 当未找到任何 PDF 文件时
        """
        all_splits: List[Document] = []

        for pdf_file in PDF_FILES:
            pdf_path = PDF_DIR / pdf_file
            if not pdf_path.exists():
                logger.warning(f"找不到文件: {pdf_path}")
                continue

            logger.info(f"正在处理 PDF: {pdf_file}")
            try:
                loader = PyPDFLoader(str(pdf_path))
                docs = loader.load()
                logger.debug(f"从 {pdf_file} 加载了 {len(docs)} 页")

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                splits = text_splitter.split_documents(docs)
                all_splits.extend(splits)
                logger.info(f"PDF {pdf_file} 分割为 {len(splits)} 个片段")

            except Exception as e:
                logger.error(f"处理 PDF {pdf_file} 时出错: {str(e)}", exc_info=True)
                continue

        if not all_splits:
            error_msg = f"未找到任何 PDF 文件在 {PDF_DIR}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"共处理 {len(all_splits)} 个文档片段，正在创建向量库...")
        self.vector_store = Chroma.from_documents(
            documents=all_splits,
            embedding_function=embeddings,
            persist_directory=DB_PATH
        )
        logger.info("向量库创建完成！")

    def get_answer(self, question: str) -> str:
        """获取问题的答案

        Args:
            question: 用户提出的问题

        Returns:
            AI 生成的答案

        Raises:
            RuntimeError: 当系统未初始化时
        """
        if not self.chain:
            error_msg = "RAG 系统未初始化"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.info(f"处理问题: {question[:100]}...")  # 只记录前100个字符
            answer = self.chain.invoke(question)
            logger.debug(f"生成答案: {answer[:200]}...")  # 只记录前200个字符
            return answer

        except Exception as e:
            logger.error(f"生成答案时出错: {str(e)}", exc_info=True)
            raise
