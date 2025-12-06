import os
import pickle

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

VECTOR_STORE_DIR = "vector_store"


# 在模块加载时 就把索引和元数据读入内存
with open(os.path.join(VECTOR_STORE_DIR, "tfidf_vectorizer.pkl"), "rb") as f:
    VECTORIZER = pickle.load(f)

with open(os.path.join(VECTOR_STORE_DIR, "doc_vectors.pkl"), "rb") as f:
    DOC_VECTORS = pickle.load(f)

with open(os.path.join(VECTOR_STORE_DIR, "chunks_meta.pkl"), "rb") as f:
    CHUNKS_META = pickle.load(f)


def search(question: str, top_k: int = 3):
    """
    返回和问题最相关的若干文本块
    """
    question_vec = VECTORIZER.transform([question])
    sims = cosine_similarity(question_vec, DOC_VECTORS)[0]  # 一维数组

    # 取相似度最高的 top_k 条
    if top_k > len(sims):
        top_k = len(sims)

    top_indices = np.argsort(sims)[::-1][:top_k]
    results = []

    for idx in top_indices:
        meta = CHUNKS_META[idx]
        score = float(sims[idx])
        results.append(
            {
                "score": score,
                "doc_name": meta["doc_name"],
                "section": meta["section"],
                "text": meta["text"],
            }
        )

    return results


def format_answer(question: str, results):
    """Build a single consolidated English answer from search results.

    This function does not call an LLM. It simply combines the most relevant
    retrieved text snippets into a single, human-readable answer. It returns
    a dict with only the `answer` key so the frontend displays a single reply.
    """
    if not results or results[0]["score"] < 0.05:
        answer = (
            "I couldn't find highly relevant information in the database. "
            "Please try rephrasing your question or check again later."
        )
        return {"answer": answer}

    # Collect the retrieved snippets (de-duplicate identical snippets)
    snippets = []
    seen = set()
    for r in results:
        text = r.get("text", "").strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        snippets.append(text)

    # Make a single consolidated answer. Simple approach: join snippets into
    # a short paragraph, separating with two line breaks for readability.
    answer_text = "\n\n".join(snippets)

    # If the combined text is long, we can prefix a short lead sentence.
    if len(answer_text) > 800:
        lead = "Based on the available documents, here is the most relevant information:\n\n"
        answer_text = lead + answer_text

    return {"answer": answer_text}


def answer_question(question: str, top_k: int = 3):
    results = search(question, top_k=top_k)
    return format_answer(question, results)
