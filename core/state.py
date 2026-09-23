"""LangGraph 全局状态定义。"""
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage

# 兼容不同版本 langgraph 的 add_messages 导入路径
try:
    from langgraph.graph import add_messages
except ImportError:  # pragma: no cover
    from langgraph.graph.message import add_messages  # type: ignore


class AgentState(TypedDict, total=False):
    # 对话消息（使用 add_messages 合并器）
    messages: Annotated[List[BaseMessage], add_messages]
    # 用户原始输入
    user_input: str
    # 调度路由：plan | schedule | knowledge
    route: str
    # 学习规划 Agent 产出的结构化计划 JSON
    plan_json: Dict[str, Any]
    # 日程 Agent 写入/查询结果
    schedule_result: str
    # 知识库 Agent 检索到的上下文片段（含来源）
    rag_context: List[Dict[str, Any]]
    # 知识库 Agent 展示用的单一来源（无命中时为「网络」）
    rag_source: str
    # 最终统一回复
    final_answer: str
