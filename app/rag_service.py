import os
import re
from pathlib import Path
from typing import List, Optional
import pdfplumber
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

from app.config import PDF_DIR, PDF_FILES, DB_PATH, LLM_MODEL, EMBED_MODEL, GROQ_API_KEY
from app.logger import setup_logger

# 初始化日志
logger = setup_logger(__name__)


def extract_course_codes(question: str) -> List[str]:
    """从问题中提取课程代码（基础代码，不包含后缀）

    支持格式:
    - mat235 -> MAT235
    - MAT235Y -> MAT235
    - STA237H1 -> STA237
    - mat224 -> MAT224

    Args:
        question: 用户问题

    Returns:
        提取到的基础课程代码列表（大写，只包含3字母+3数字）
    """
    # 匹配课程代码模式：3个字母 + 3个数字（忽略后缀）
    pattern = r'\b([A-Z]{3}\d{3})'
    matches = re.findall(pattern, question, re.IGNORECASE)

    # 转换为大写并去重
    course_codes = list(set(match.upper() for match in matches))

    if course_codes:
        logger.info(f"从问题中提取到课程代码: {course_codes}")
    else:
        logger.debug("未从问题中提取到课程代码")

    return course_codes

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
            embeddings = HuggingFaceEmbeddings(
                model_name=EMBED_MODEL,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            logger.info(f"初始化 LLM 模型: {LLM_MODEL}")
            llm = ChatGroq(
                groq_api_key=GROQ_API_KEY,
                model_name=LLM_MODEL,
                temperature=0
            )

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
            You are an intelligent teaching assistant with access to multiple course documents and materials.

            Answer the student's question based ONLY on the context provided below.
            The context may come from different courses or documents - each piece has metadata showing its source.

            IMPORTANT INSTRUCTIONS:
            1. If the answer is in the context, provide a clear and helpful response
            2. At the end of your answer, cite the source(s) by mentioning the course/document name (e.g., "Source: MAT235Y")
            3. If information comes from multiple sources, list all of them
            4. If the answer is not in any of the provided context, say "I cannot find this information in the available documents."
            5. You can synthesize information from multiple courses if relevant to the question

            Context (with source metadata):
            {context}

            Question:
            {question}

            Answer (remember to cite sources):
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

    def _extract_tables_from_pdf(self, pdf_path: Path) -> List[str]:
        """从 PDF 中提取所有表格并格式化为文本

        Args:
            pdf_path: PDF 文件路径

        Returns:
            格式化的表格文本列表
        """
        tables_text = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 提取该页的所有表格
                    tables = page.extract_tables()

                    if tables:
                        logger.debug(f"在第 {page_num} 页找到 {len(tables)} 个表格")

                        for table_idx, table in enumerate(tables, start=1):
                            if not table or len(table) == 0:
                                continue

                            # 格式化表格为文本
                            table_text = f"\n[Table from Page {page_num}, Table {table_idx}]\n"

                            # 处理表头
                            if len(table) > 0 and table[0]:
                                header = " | ".join([str(cell) if cell else "" for cell in table[0]])
                                table_text += header + "\n"
                                table_text += "-" * len(header) + "\n"

                            # 处理表格内容
                            for row in table[1:]:
                                if row:
                                    row_text = " | ".join([str(cell) if cell else "" for cell in row])
                                    table_text += row_text + "\n"

                            tables_text.append(table_text)
                            logger.debug(f"提取表格: {table_text[:100]}...")

        except Exception as e:
            logger.warning(f"提取表格时出错: {str(e)}")

        return tables_text

    def _load_pdfs_to_vector_store(self, embeddings: HuggingFaceEmbeddings) -> None:
        """加载所有 PDF 文件到向量数据库，为每个文档添加元数据

        Args:
            embeddings: HuggingFace 嵌入模型实例

        Raises:
            FileNotFoundError: 当未找到任何 PDF 文件时
        """
        all_splits: List[Document] = []

        for pdf_file in PDF_FILES:
            pdf_path = PDF_DIR / pdf_file
            if not pdf_path.exists():
                logger.warning(f"找不到文件: {pdf_path}")
                continue

            # 从文件名提取课程信息（例如：MAT235Y.pdf -> MAT235Y）
            course_name = pdf_path.stem  # 去掉 .pdf 后缀
            logger.info(f"正在处理文档: {pdf_file} (课程/文档: {course_name})")

            try:
                # 1. 使用 PyPDFLoader 加载普通文本
                loader = PyPDFLoader(str(pdf_path))
                docs = loader.load()
                logger.debug(f"从 {pdf_file} 加载了 {len(docs)} 页文本")

                # 为每个文档页添加元数据
                for doc in docs:
                    doc.metadata["source_file"] = pdf_file
                    doc.metadata["course"] = course_name
                    doc.metadata["content_type"] = "text"
                    # 保留原有的 page 信息（如果有）
                    if "page" not in doc.metadata:
                        doc.metadata["page"] = 0

                # 2. 使用 pdfplumber 提取表格
                logger.info(f"正在提取 {pdf_file} 中的表格...")
                tables_text = self._extract_tables_from_pdf(pdf_path)

                if tables_text:
                    logger.info(f"从 {pdf_file} 中提取了 {len(tables_text)} 个表格")
                    # 将每个表格创建为独立的文档
                    for idx, table_text in enumerate(tables_text):
                        table_doc = Document(
                            page_content=table_text,
                            metadata={
                                "source_file": pdf_file,
                                "course": course_name,
                                "content_type": "table",
                                "table_index": idx + 1
                            }
                        )
                        docs.append(table_doc)
                else:
                    logger.debug(f"{pdf_file} 中未找到表格")

                # 3. 分割文档（文本和表格）
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1500,  # 增加 chunk_size 以更好地保留表格
                    chunk_overlap=300
                )
                splits = text_splitter.split_documents(docs)

                # 确保分割后的文档也保留元数据
                for split in splits:
                    split.metadata["source_file"] = pdf_file
                    split.metadata["course"] = course_name

                all_splits.extend(splits)
                logger.info(f"文档 {pdf_file} 处理完成：{len(splits)} 个片段（包含表格）")

            except Exception as e:
                logger.error(f"处理文档 {pdf_file} 时出错: {str(e)}", exc_info=True)
                continue

        if not all_splits:
            error_msg = f"未找到任何 PDF 文件在 {PDF_DIR}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"共处理 {len(all_splits)} 个文档片段，来自 {len(PDF_FILES)} 个文件")
        logger.info("正在创建向量库...")
        self.vector_store = Chroma.from_documents(
            documents=all_splits,
            embedding=embeddings,
            persist_directory=DB_PATH
        )
        logger.info("向量库创建完成！支持跨文档搜索")

    def get_answer(self, question: str) -> str:
        """获取问题的答案，支持智能课程过滤

        Args:
            question: 用户提出的问题

        Returns:
            AI 生成的答案

        Raises:
            RuntimeError: 当系统未初始化时
        """
        if not self.vector_store:
            error_msg = "RAG 系统未初始化"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.info(f"处理问题: {question[:100]}...")

            # 1. 从问题中提取课程代码
            course_codes = extract_course_codes(question)

            # 2. 根据是否找到课程代码，使用不同的检索策略
            if course_codes:
                # 找到课程代码 - 精准检索
                logger.info(f"使用课程过滤检索: {course_codes}")

                # 从所有匹配的课程中检索
                all_docs = []
                for course_code in course_codes:
                    try:
                        # 先尝试精确匹配课程代码
                        docs = self.vector_store.similarity_search(
                            question,
                            k=5,  # 每个课程检索 5 个文档
                            filter={"course": course_code}
                        )

                        # 如果精确匹配没有结果，尝试前缀匹配（course_code 是基础代码，metadata 可能有后缀）
                        if not docs:
                            logger.debug(f"精确匹配 {course_code} 无结果，尝试检索所有文档并过滤")
                            # 检索更多文档并手动过滤
                            temp_docs = self.vector_store.similarity_search(question, k=20)
                            docs = [doc for doc in temp_docs if doc.metadata.get("course", "").startswith(course_code)]

                        all_docs.extend(docs)
                        logger.info(f"从 {course_code} 检索到 {len(docs)} 个文档")
                    except Exception as e:
                        logger.warning(f"检索课程 {course_code} 时出错: {e}")
                        continue

                if not all_docs:
                    logger.warning(f"未找到课程 {course_codes} 的文档，尝试全局检索")
                    all_docs = self.vector_store.similarity_search(question, k=10)

                # 手动构建上下文
                context = "\n\n".join([doc.page_content for doc in all_docs])

            else:
                # 未找到课程代码 - 跨课程检索
                logger.info("未找到课程代码，使用跨课程检索（K=10）")
                all_docs = self.vector_store.similarity_search(question, k=10)
                context = "\n\n".join([doc.page_content for doc in all_docs])

            # 3. 构建 prompt 并生成答案
            llm = ChatGroq(
                groq_api_key=GROQ_API_KEY,
                model_name=LLM_MODEL,
                temperature=0
            )

            template = """
            You are an intelligent teaching assistant with access to multiple course documents and materials.

            Answer the student's question based ONLY on the context provided below.
            The context may come from different courses or documents - each piece has metadata showing its source.

            IMPORTANT INSTRUCTIONS:
            1. If the answer is in the context, provide a clear and helpful response
            2. At the end of your answer, cite the source(s) by mentioning the course/document name (e.g., "Source: MAT235Y1")
            3. If information comes from multiple sources, list all of them
            4. If the answer is not in any of the provided context, say "I cannot find this information in the available documents."
            5. You can synthesize information from multiple courses if relevant to the question

            Context (with source metadata):
            {context}

            Question:
            {question}

            Answer (remember to cite sources):
            """

            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_template(template)

            # 生成答案
            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({"context": context, "question": question})

            logger.info(f"成功生成答案，长度: {len(answer)} 字符")
            logger.debug(f"生成答案: {answer[:200]}...")

            return answer

        except Exception as e:
            logger.error(f"生成答案时出错: {str(e)}", exc_info=True)
            raise
