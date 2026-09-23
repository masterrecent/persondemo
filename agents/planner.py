"""学习规划 Agent：根据学习目标输出结构化计划 JSON。"""
import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.llm import get_llm
from core.state import AgentState

PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一个学习规划专家。根据用户的学习目标，输出一份结构化的学习计划 JSON。\n"
            "要求：\n"
            "1. 严格输出 JSON，不要包含 markdown 代码块标记或额外文字。\n"
            "2. JSON 结构为：{{\"goal\": \"...\", \"total_days\": N, \"tasks\": [{{\"day\": 1, \"topic\": \"...\", \"content\": \"...\"}}, ...]}}\n"
            "3. 每天的 topic 简短明确，content 说明当天要完成的具体学习内容。\n"
            "4. 任务覆盖完整的学习周期，难度循序渐进。",
        ),
        ("human", "{input}"),
    ]
)


def planner_node(state: AgentState) -> dict:
    user_input = state.get("user_input") or state["messages"][-1].content
    chain = PLANNER_PROMPT | get_llm() | JsonOutputParser()
    try:
        plan = chain.invoke({"input": user_input})
    except Exception:
        # JSON 解析失败时用纯文本二次兜底
        raw = (PLANNER_PROMPT | get_llm()).invoke({"input": user_input}).content
        plan = _safe_json(raw)
    if not isinstance(plan, dict):
        plan = {"goal": user_input, "total_days": 0, "tasks": []}
    plan.setdefault("goal", user_input)
    plan.setdefault("tasks", [])
    return {"plan_json": plan}


def _safe_json(text: str) -> dict:
    import re

    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"goal": "", "total_days": 0, "tasks": []}
