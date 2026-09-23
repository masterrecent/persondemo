# 微信云托管部署镜像：知序 · 多 Agent 学习助手
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_DISABLE_SYMLINKS=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2 \
    PORT=80

WORKDIR /app

# faiss / sentence-transformers 运行所需的系统库
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先装 CPU 版 torch，避免默认 wheel 拉入数 GB 的 CUDA 依赖
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 构建期预下载 embedding 模型，避免容器冷启动时联网下载导致首次请求超时
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['EMBEDDING_MODEL'])"

COPY . .

# 构建期预生成 FAISS 索引，避免首次知识库问答时才建索引而触发 60 秒超时
RUN python -c "from core.llm import get_embeddings; from rag.ingest import get_vectorstore; get_vectorstore(get_embeddings(), rebuild=True)"

EXPOSE 80

CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-80}"]
