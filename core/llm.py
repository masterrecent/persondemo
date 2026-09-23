"""LLM 与 Embedding 配置（OpenAI 兼容接口 + 本地 sentence-transformers）。"""
import os
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings

load_dotenv()

# 兼容 Windows 下 huggingface_hub 无法创建 symlink 的问题
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
# 国内网络默认使用 HuggingFace 镜像，避免直连超时
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def get_llm() -> ChatOpenAI:
    """获取可配置的 OpenAI 兼容大模型实例。"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv(
        "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model = os.getenv("MODEL_NAME", "qwen-plus")
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.3,
    )


class LocalEmbeddings(Embeddings):
    """基于 sentence-transformers 的本地 embedding，避免依赖外部 embedding API。"""

    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer

        name = model_name or os.getenv(
            "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self._model = SentenceTransformer(name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(text, normalize_embeddings=True, show_progress_bar=False).tolist()


_embeddings_instance: LocalEmbeddings | None = None


def get_embeddings() -> LocalEmbeddings:
    """单例获取 embedding 模型，避免重复加载。"""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = LocalEmbeddings()
    return _embeddings_instance
