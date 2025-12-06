import os
import glob
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer

DATA_DIR = "data_docs"
VECTOR_STORE_DIR = "vector_store"


def load_documents():
    docs = []
    for path in glob.glob(os.path.join(DATA_DIR, "*.md")):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        docs.append({"doc_name": os.path.basename(path), "text": text})
    return docs


def split_into_chunks(doc_text, min_len=50):
    """
    按空行切段 太短的段落会合并
    """
    raw_parts = doc_text.split("\n\n")
    chunks = []

    buffer = []
    for part in raw_parts:
        stripped = part.strip()
        if not stripped:
            continue
        buffer.append(stripped)
        # 简单判断长度
        if sum(len(p) for p in buffer) >= min_len:
            chunks.append("\n\n".join(buffer))
            buffer = []

    if buffer:
        chunks.append("\n\n".join(buffer))

    return chunks


def build_index():
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    docs = load_documents()
    all_chunks = []
    for doc in docs:
        chunks = split_into_chunks(doc["text"])
        for idx, chunk in enumerate(chunks):
            all_chunks.append(
                {
                    "doc_name": doc["doc_name"],
                    "section": f"chunk-{idx}",
                    "text": chunk,
                }
            )

    if not all_chunks:
        raise RuntimeError("没有找到任何文档内容 请先在 data_docs 中放入 md 文件")

    texts = [c["text"] for c in all_chunks]

    # 建立 TF-IDF 向量
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words=None,
    )
    doc_vectors = vectorizer.fit_transform(texts)

    # 保存向量器 向量矩阵 元数据
    with open(os.path.join(VECTOR_STORE_DIR, "tfidf_vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)

    with open(os.path.join(VECTOR_STORE_DIR, "doc_vectors.pkl"), "wb") as f:
        pickle.dump(doc_vectors, f)

    with open(os.path.join(VECTOR_STORE_DIR, "chunks_meta.pkl"), "wb") as f:
        pickle.dump(all_chunks, f)

    print(f"索引构建完成 共 {len(all_chunks)} 个文本块")


if __name__ == "__main__":
    build_index()
