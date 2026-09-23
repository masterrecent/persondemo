"""LangGraph 多 Agent 工作流组装：Supervisor 路由 → 子 Agent → 统一渲染。"""
from langgraph.graph import END, START, StateGraph

from agents.knowledge_agent import knowledge_node
from agents.planner import planner_node
from agents.schedule_agent import schedule_query_node, schedule_write_node
from agents.supervisor import supervisor_node
from core.state import AgentState


def render_node(state: AgentState) -> dict:
    """统一回复渲染：根据路由聚合各 Agent 结果。"""
    route = state.get("route")
    if route == "plan":
        plan = state.get("plan_json") or {}
        schedule_result = state.get("schedule_result", "")
        tasks = plan.get("tasks", [])
        lines = [f"学习目标：{plan.get('goal', '')}", f"共 {plan.get('total_days', len(tasks))} 天计划："]
        for t in tasks:
            lines.append(f"  Day {t.get('day')}: {t.get('topic')} - {t.get('content')}")
        lines.append("")
        lines.append(schedule_result)
        return {"final_answer": "\n".join(lines)}

    if route == "schedule":
        return {"final_answer": state.get("schedule_result", "暂无日程信息。")}

    if route == "knowledge":
        return {"final_answer": state.get("final_answer", "未找到相关知识。")}

    return {"final_answer": "无法识别的请求。"}


def build_graph():
    """构建并编译多 Agent 工作流。"""
    builder = StateGraph(AgentState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("planner", planner_node)
    builder.add_node("schedule_write", schedule_write_node)
    builder.add_node("schedule_query", schedule_query_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("render", render_node)

    builder.add_edge(START, "supervisor")

    # 路由分发
    def route_after_supervisor(state: AgentState) -> str:
        r = state.get("route")
        if r == "plan":
            return "planner"
        if r == "schedule":
            return "schedule_query"
        return "knowledge"

    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "planner": "planner",
            "schedule_query": "schedule_query",
            "knowledge": "knowledge",
        },
    )

    # 规划 → 写入日程 → 渲染
    builder.add_edge("planner", "schedule_write")
    builder.add_edge("schedule_write", "render")
    # 日程查询 → 渲染
    builder.add_edge("schedule_query", "render")
    # 知识库 → 渲染
    builder.add_edge("knowledge", "render")

    builder.add_edge("render", END)

    return builder.compile()


# 全局单例
graph = build_graph()
