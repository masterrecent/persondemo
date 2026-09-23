"""调度 Agent（Supervisor）：识别用户意图，路由到 plan / schedule / knowledge。"""
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.llm import get_llm
from core.state import AgentState

SUPERVISOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一个多 Agent 系统的调度器（Supervisor）。根据用户输入判断意图，只输出一个路由标签，不要解释。\n"
            "可选路由：\n"
            "- plan：用户想制定学习计划（如'我要X天学完Y'、'帮我安排学习计划'）\n"
            "- schedule：用户想查看今天/当前该学什么（如'今天该学什么'、'今日任务'）\n"
            "- knowledge：用户询问某个知识点，或基于上传文档提问（如'什么是StateGraph'、'解释一下XX'）\n"
            "只输出 plan / schedule / knowledge 三者之一。",
        ),
        ("human", "{input}"),
    ]
)


def parse_route(text: str) -> str:
    text = text.strip().lower()
    for tag in ("plan", "schedule", "knowledge"):
        if tag in text:
            return tag
    # 兜底：正则提取
    m = re.search(r"(plan|schedule|knowledge)", text)
    return m.group(1) if m else "knowledge"


def supervisor_node(state: AgentState) -> dict:
    user_input = state.get("user_input") or state["messages"][-1].content
    chain = SUPERVISOR_PROMPT | get_llm() | StrOutputParser()
    raw = chain.invoke({"input": user_input})
    route = parse_route(raw)
    return {"route": route}
