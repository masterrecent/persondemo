"""文档摄入：仅加载用户明确导入的文件，并写入 FAISS CPU 向量库。"""
import json
import os
from typing import Iterable, List

from langchain_core.documents import Document

# 多版本兼容导入
try:
    from langchain_community.document_loaders import PyPDFLoader, TextLoader
except ImportError:  # pragma: no cover
    from langchain.document_loaders import PyPDFLoader, TextLoader  # type: ignore

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

try:
    from langchain_community.vectorstores import FAISS
except ImportError:  # pragma: no cover
    from langchain.vectorstores import FAISS  # type: ignore

DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", os.path.join("data", "documents"))
FAISS_DIR = os.getenv("FAISS_DIR", "faiss_index")
IMPORTED_MANIFEST = os.path.join(FAISS_DIR, "imported_documents.json")
SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md")


def ensure_dirs() -> None:
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    os.makedirs(FAISS_DIR, exist_ok=True)


def _valid_document_name(name: str) -> bool:
    return bool(name) and os.path.basename(name) == name and name.lower().endswith(SUPPORTED_EXTENSIONS)


def get_imported_document_names() -> List[str]:
    """返回已明确导入且当前仍存在的文档名称。"""
    ensure_dirs()
    try:
        with open(IMPORTED_MANIFEST, "r", encoding="utf-8") as stream:
            stored = json.load(stream)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    if not isinstance(stored, list):
        return []
    return sorted(
        {
            name for name in stored
            if isinstance(name, str)
            and _valid_document_name(name)
            and os.path.isfile(os.path.join(DOCUMENTS_DIR, name))
        }
    )


def set_imported_document_names(names: Iterable[str]) -> List[str]:
    """原子更新导入清单；目录中的其他文件继续保持待导入状态。"""
    ensure_dirs()
    imported = sorted(
        {
            name for name in names
            if _valid_document_name(name)
            and os.path.isfile(os.path.join(DOCUMENTS_DIR, name))
        }
    )
    temporary = f"{IMPORTED_MANIFEST}.tmp"
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(imported, stream, ensure_ascii=False, indent=2)
    os.replace(temporary, IMPORTED_MANIFEST)
    return imported


def load_documents() -> List[Document]:
    """只加载导入清单中的 PDF、TXT 和 Markdown 文件。"""
    ensure_dirs()
    docs: List[Document] = []
    for filename in get_imported_document_names():
        path = os.path.join(DOCUMENTS_DIR, filename)
        lower = filename.lower()
        try:
            if lower.endswith(".pdf"):
                docs.extend(PyPDFLoader(path).load())
            elif lower.endswith((".txt", ".md")):
                for enc in ("utf-8", "gbk", "latin-1"):
                    try:
                        docs.extend(TextLoader(path, encoding=enc).load())
                        break
                    except UnicodeDecodeError:
                        continue
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] 加载 {filename} 失败: {e}")
    return docs


def build_index(embeddings) -> FAISS:
    """切分文档并构建 FAISS 索引，保存到本地。"""
    docs = load_documents()
    if not docs:
        # 空文档时插入占位，避免 FAISS 初始化失败
        docs = [Document(page_content="(暂无文档内容)", metadata={"source": "empty"})]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(FAISS_DIR)
    return vectorstore


def get_vectorstore(embeddings, rebuild: bool = False) -> FAISS:
    """获取 FAISS 向量库；不存在或要求重建时重新构建。"""
    ensure_dirs()
    index_file = os.path.join(FAISS_DIR, "index.faiss")
    if rebuild or not os.path.exists(index_file):
        return build_index(embeddings)
    return FAISS.load_local(
        FAISS_DIR, embeddings, allow_dangerous_deserialization=True
    )


def add_file_to_index(file_path: str, embeddings) -> int:
    """为兼容旧调用增量处理已导入文件；候选文件不会被自动摄入。"""
    ensure_dirs()
    if not os.path.exists(file_path):
        return 0
    filename = os.path.basename(file_path)
    if filename not in get_imported_document_names():
        return 0
    lower = filename.lower()
    try:
        if lower.endswith(".pdf"):
            docs = PyPDFLoader(file_path).load()
        else:
            docs = []
            for enc in ("utf-8", "gbk", "latin-1"):
                try:
                    docs = TextLoader(file_path, encoding=enc).load()
                    break
                except UnicodeDecodeError:
                    continue
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 加载 {file_path} 失败: {e}")
        return 0
    if not docs:
        return 0
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    vs = get_vectorstore(embeddings)
    vs.add_documents(chunks)
    vs.save_local(FAISS_DIR)
    return len(chunks)
