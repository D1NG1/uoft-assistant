"""
RAG Service 单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.rag_service import RAGService
from app.config import PDF_DIR, DB_PATH


class TestRAGService:
    """RAG Service 测试类"""

    @patch('app.rag_service.OllamaEmbeddings')
    @patch('app.rag_service.ChatOllama')
    @patch('app.rag_service.Chroma')
    @patch('os.path.exists')
    def test_initialization_with_existing_db(
        self,
        mock_exists,
        mock_chroma,
        mock_chat_ollama,
        mock_embeddings
    ):
        """测试使用已有数据库初始化"""
        # 模拟数据库已存在
        mock_exists.return_value = True
        mock_vector_store = MagicMock()
        mock_chroma.return_value = mock_vector_store
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever

        # 初始化服务
        service = RAGService()

        # 断言
        assert service.vector_store is not None
        assert service.retriever is not None
        assert service.chain is not None
        mock_chroma.assert_called_once()

    @patch('app.rag_service.OllamaEmbeddings')
    @patch('app.rag_service.ChatOllama')
    @patch('app.rag_service.os.path.exists')
    @patch('app.rag_service.PyPDFLoader')
    @patch('app.rag_service.Chroma.from_documents')
    def test_initialization_without_db(
        self,
        mock_from_documents,
        mock_pdf_loader,
        mock_exists,
        mock_chat_ollama,
        mock_embeddings
    ):
        """测试从 PDF 创建新数据库"""
        # 模拟数据库不存在
        mock_exists.return_value = False

        # 模拟 PDF 加载
        mock_loader = MagicMock()
        mock_pdf_loader.return_value = mock_loader
        mock_docs = [MagicMock(page_content="test content")]
        mock_loader.load.return_value = mock_docs

        # 模拟向量库
        mock_vector_store = MagicMock()
        mock_from_documents.return_value = mock_vector_store
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever

        # 初始化服务
        service = RAGService()

        # 断言
        assert service.vector_store is not None
        assert mock_pdf_loader.called

    def test_get_answer_without_initialization(self):
        """测试未初始化时获取答案"""
        with patch('app.rag_service.OllamaEmbeddings'), \
             patch('app.rag_service.ChatOllama'), \
             patch('app.rag_service.Chroma'), \
             patch('os.path.exists', return_value=True):

            service = RAGService()
            service.chain = None  # 强制设为 None

            with pytest.raises(RuntimeError, match="RAG 系统未初始化"):
                service.get_answer("test question")

    @patch('app.rag_service.OllamaEmbeddings')
    @patch('app.rag_service.ChatOllama')
    @patch('app.rag_service.Chroma')
    @patch('os.path.exists')
    def test_get_answer_success(
        self,
        mock_exists,
        mock_chroma,
        mock_chat_ollama,
        mock_embeddings
    ):
        """测试成功获取答案"""
        # 模拟数据库已存在
        mock_exists.return_value = True
        mock_vector_store = MagicMock()
        mock_chroma.return_value = mock_vector_store
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever

        # 初始化服务
        service = RAGService()

        # 模拟 chain 的 invoke 方法
        mock_answer = "This is a test answer"
        service.chain = MagicMock()
        service.chain.invoke.return_value = mock_answer

        # 调用方法
        result = service.get_answer("What is the course about?")

        # 断言
        assert result == mock_answer
        service.chain.invoke.assert_called_once_with("What is the course about?")
