import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class SyllabusRAG:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        # 本地向量数据库的存储路径
        self.vector_store_path = "./chroma_db"
        self.model_name = "llama3"
        
        # 1. 初始化 Embedding 模型 (负责将英文文本转为向量)
        print(f"--- 正在初始化 Embedding 模型 ({self.model_name}) ---")
        self.embeddings = OllamaEmbeddings(model=self.model_name)
        
        # 2. 初始化 LLM (负责用英文思考和回答)
        self.llm = ChatOllama(model=self.model_name)
        
        # 3. 检查数据库是否存在，不存在则处理 PDF
        if not os.path.exists(self.vector_store_path):
            print("--- 未发现向量库，正在处理 PDF... ---")
            self.ingest_pdf()
        else:
            print("--- 发现已有向量库，直接加载 ---")
            
        # 4. 连接 ChromaDB 数据库
        self.vector_store = Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )
        
        # 5. 设置检索器 (Retriever)
        # search_kwargs={"k": 5}: 每次检索最相关的 5 个片段
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )

    def ingest_pdf(self):
        """读取 PDF -> 切块 -> 存入向量库"""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"文件不存在: {self.pdf_path}")

        print(f"--- 正在加载文件: {self.pdf_path} ---")
        loader = PyPDFLoader(self.pdf_path)
        docs = loader.load()
        
        # 切分文本
        # chunk_size=1000: 英文通常 1000 个字符包含的信息量比较合适
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        # 存入数据库
        print(f"--- 正在存入 {len(splits)} 个文本块到 ChromaDB... ---")
        Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=self.vector_store_path
        )
        print("✅ 处理完成！")

    def get_answer(self, question):
        """核心 RAG 链条"""
        
        # --- 这里改成了英文 Prompt ---
        # 这种 Prompt 结构被称为 "Context-QA" 模式
        template = """
        You are an intelligent teaching assistant for the University of Toronto course MAT235.
        Use the following pieces of retrieved context to answer the student's question.
        
        Rules:
        1. Answer based ONLY on the context provided below.
        2. If the answer is not in the context, strictly state: "I cannot find this information in the syllabus."
        3. Keep your answer concise and professional.
        
        Context:
        {context}
        
        Student Question:
        {question}
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # 构建 LCEL (LangChain Expression Language) 流水线
        rag_chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return rag_chain.invoke(question)

# 简单测试块
if __name__ == "__main__":
    # 确保 data 文件夹里有 syllabus.pdf
    bot = SyllabusRAG("data/MAT235Y12025-26Syllabus.pdf")
    # 测试一个英文问题
    print(bot.get_answer("What is the weight of the final exam?"))