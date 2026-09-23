"""知识库 Agent：基于 FAISS 的 RAG 检索 + 单一来源引用。"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.llm import get_llm
from core.state import AgentState
from rag.retriever import retrieve, top_source

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一个学习助手。请依据下面提供的知识库片段回答用户问题，"
            "回答要条理清晰、简洁准确，不要编造片段中不存在的事实。"
            "请使用纯文本，不要输出 Markdown 加粗等格式标记。\n\n"
            "知识库片段：\n{context}",
        ),
        ("human", "{question}"),
    ]
)

FALLBACK_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一个学习助手。本次知识库中没有检索到与问题相关的内容，"
            "请基于大模型的通用知识回答用户问题，并在开头用一句话说明"
            "「知识库中未找到相关内容，以下回答由大模型基于通用知识生成」。"
            "回答要条理清晰、简洁准确；对时效性或不确定的信息明确提醒用户核实。"
            "请使用纯文本，不要输出 Markdown 加粗等格式标记。",
        ),
        ("human", "{question}"),
    ]
)

RELEVANCE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是知识库检索结果审核器。判断给出的知识库片段是否直接包含回答用户问题所需的事实。\n"
            "只有片段与问题主题一致、且信息足以支持回答时才输出 relevant。\n"
            "仅仅出现相似技术词、宽泛概念或无关上下文时必须输出 irrelevant。\n"
            "只输出 relevant 或 irrelevant，不要解释。\n\n知识库片段：\n{context}",
        ),
        ("human", "{question}"),
    ]
)


def _context_is_relevant(question: str, context: str, llm) -> bool:
    """用大模型复核向量召回，避免低相关片段被误标为知识库来源。"""
    verdict = (RELEVANCE_PROMPT | llm | StrOutputParser()).invoke(
        {"context": context, "question": question}
    )
    return verdict.strip().lower() == "relevant"


def knowledge_node(state: AgentState) -> dict:
    user_input = state.get("user_input") or state["messages"][-1].content

    contexts = retrieve(user_input, k=4)
    llm = get_llm()
    if contexts:
        context_str = "\n\n".join(
            f"[片段{i}] {c['content']}" for i, c in enumerate(contexts, 1)
        )
        if not _context_is_relevant(user_input, context_str, llm):
            contexts = []

    if contexts:
        chain = RAG_PROMPT | llm | StrOutputParser()
        answer = chain.invoke({"context": context_str, "question": user_input})
    else:
        chain = FALLBACK_PROMPT | llm | StrOutputParser()
        answer = chain.invoke({"question": user_input})

    source = top_source(contexts)
    return {"rag_context": contexts, "rag_source": source, "final_answer": answer}
