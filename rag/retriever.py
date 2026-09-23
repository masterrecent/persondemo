"""RAG 检索：基于 FAISS 的相似度检索 + 相关性过滤 + 单一来源。"""
import os
from typing import Any, Dict, List, Optional

from core.llm import get_embeddings
from rag.ingest import get_imported_document_names, get_vectorstore

# FAISS 使用归一化向量的 L2 距离，距离越小越相关：cos = 1 - distance / 2
# 默认阈值 1.1 约等于余弦相似度 0.45；召回后还会由知识库 Agent 做相关性复核。
DEFAULT_MAX_DISTANCE = 1.1


def retrieve(
    query: str, k: int = 4, max_distance: Optional[float] = DEFAULT_MAX_DISTANCE
) -> List[Dict[str, Any]]:
    """检索与 query 最相关的 k 个片段，按相关性过滤后返回。"""
    embeddings = get_embeddings()
    vs = get_vectorstore(embeddings)
    pairs = vs.similarity_search_with_score(query, k=k)
    imported = set(get_imported_document_names())

    results: List[Dict[str, Any]] = []
    for doc, distance in pairs:
        if doc.metadata.get("source") == "empty":
            continue
        if os.path.basename(doc.metadata.get("source", "")) not in imported:
            continue
        if max_distance is not None and distance > max_distance:
            continue
        results.append(
            {
                "rank": len(results) + 1,
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page"),
                "score": round(1 - distance / 2, 3),
            }
        )
    return results


def top_source(contexts: List[Dict[str, Any]]) -> str:
    """取最相关片段的来源文件名；无命中时返回「网络」。"""
    if not contexts:
        return "网络"
    name = os.path.basename(contexts[0].get("source", "")) or "网络"
    page = contexts[0].get("page")
    if page is not None:
        name += f"（第{page}页）"
    return name
