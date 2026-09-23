"""日程提醒 Agent：写入学习计划到 SQLite、查询今日任务。"""
from db.sqlite_db import get_plan_overview, get_today_tasks, save_plan
from core.state import AgentState


def schedule_write_node(state: AgentState) -> dict:
    """接收学习规划 JSON，写入 SQLite 日程表。"""
    plan = state.get("plan_json") or {}
    saved = save_plan(plan, source_prompt=state.get("user_input", ""))
    overview = get_plan_overview(saved["plan_id"])
    result = (
        f"已新增一条学习计划，共 {saved['count']} 条任务，"
        f"计划从 {overview['start_date']} 开始，共 {overview['total_days']} 天。"
    )
    return {"schedule_result": result}


def schedule_query_node(state: AgentState) -> dict:
    """查询今日应学习的任务。"""
    tasks = get_today_tasks()
    overview = get_plan_overview()
    if not tasks:
        if overview["total_days"] == 0:
            result = "当前还没有学习计划，请先告诉我你的学习目标，我来帮你安排。"
        else:
            result = (
                f"当前计划共 {overview['total_days']} 天，起始日 {overview['start_date']}，"
                "今天没有对应的任务安排。"
            )
        return {"schedule_result": result}

    lines = [f"今天共有 {len(tasks)} 项学习任务："]
    for t in tasks:
        lines.append(f"- 【{t['plan_goal']} / Day {t['day']}】{t['topic']}：{t['content']}")
    return {"schedule_result": "\n".join(lines)}
