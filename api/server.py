"""FastAPI 服务：多 Agent 学习助手的 HTTP 接口 + 前端静态页面。"""
import os
import re
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.llm import get_embeddings
from db.sqlite_db import (
    add_course,
    check_in_today,
    clear_courses,
    delete_course,
    delete_plan,
    get_checkins,
    get_courses,
    get_focus_sessions,
    get_follow_up_plans,
    get_learning_stats,
    get_full_plan,
    get_plan_overview,
    get_today_tasks,
    init_db,
    replace_external_courses,
    save_focus_session,
    update_task,
)
from graph import graph
from ics_parser import ICSParseError, fetch_ics, parse_ics
from rag.ingest import (
    DOCUMENTS_DIR,
    get_imported_document_names,
    get_vectorstore,
    set_imported_document_names,
)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT_DIR, "web")

ALLOWED_EXT = (".pdf", ".txt", ".md")

app = FastAPI(title="多 Agent 学习助手", version="1.0.0")


class ChatRequest(BaseModel):
    message: str


class TaskUpdateRequest(BaseModel):
    completed: bool
    rating: int | None = None
    review: str = ""


class FocusSessionRequest(BaseModel):
    duration_seconds: int
    task_name: str = ""
    mode: str = "focus"
    completed: bool = True
    started_at: str | None = None


class CourseCreateRequest(BaseModel):
    name: str
    day_of_week: int
    start_time: str
    end_time: str
    location: str = ""
    teacher: str = ""
    weeks_text: str = ""


class CourseUrlImportRequest(BaseModel):
    url: str


def _document_names() -> List[str]:
    if not os.path.isdir(DOCUMENTS_DIR):
        return []
    return sorted(
        name for name in os.listdir(DOCUMENTS_DIR)
        if name.lower().endswith(ALLOWED_EXT) and os.path.isfile(os.path.join(DOCUMENTS_DIR, name))
    )


def _document_path(filename: str) -> str:
    name = (filename or "").strip()
    if not name or os.path.basename(name) != name or not name.lower().endswith(ALLOWED_EXT):
        raise HTTPException(status_code=400, detail="文档名称或类型不合法")
    root = os.path.abspath(DOCUMENTS_DIR)
    path = os.path.abspath(os.path.join(root, name))
    if os.path.commonpath([root, path]) != root:
        raise HTTPException(status_code=400, detail="文档路径不合法")
    return path


def _rebuild_documents() -> int:
    try:
        vectorstore = get_vectorstore(get_embeddings(), rebuild=True)
        return len(vectorstore.docstore._dict) if get_imported_document_names() else 0
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"重建知识索引失败：{exc}") from exc


def _knowledge_state(chunks: int | None = None) -> Dict[str, Any]:
    imported = get_imported_document_names()
    imported_set = set(imported)
    available = [name for name in _document_names() if name not in imported_set]
    result: Dict[str, Any] = {
        "documents": imported,
        "imported_documents": imported,
        "available_documents": available,
    }
    if chunks is not None:
        result["chunks"] = chunks
    return result


def _replace_imported_documents(names: List[str]) -> Dict[str, Any]:
    previous = get_imported_document_names()
    selected = set_imported_document_names(names)
    try:
        return _knowledge_state(_rebuild_documents())
    except HTTPException:
        set_imported_document_names(previous)
        try:
            _rebuild_documents()
        except HTTPException:
            pass
        raise


def _validate_month(month: str) -> str:
    try:
        year, month_number = (int(part) for part in month.split("-"))
        if not 1 <= month_number <= 12:
            raise ValueError
        return f"{year:04d}-{month_number:02d}"
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="月份格式应为 YYYY-MM") from None


def _build_trace(route: str, result: Dict[str, Any]) -> List[Dict[str, str]]:
    """把一次执行的 Agent 链路整理成前端可渲染的步骤列表。"""
    steps = [{"agent": "Supervisor", "desc": f"识别意图 → route={route}"}]
    if route == "plan":
        plan = result.get("plan_json") or {}
        steps.append(
            {
                "agent": "学习规划 Agent",
                "desc": f"生成结构化计划 JSON，共 {len(plan.get('tasks', []))} 条任务",
            }
        )
        steps.append(
            {
                "agent": "日程 Agent",
                "desc": result.get("schedule_result", "写入 SQLite 日程表"),
            }
        )
    elif route == "schedule":
        steps.append(
            {"agent": "日程 Agent", "desc": result.get("schedule_result", "查询 SQLite 日程表")}
        )
    elif route == "knowledge":
        ctx = result.get("rag_context") or []
        if ctx:
            steps.append(
                {"agent": "知识库 Agent", "desc": f"FAISS 检索命中 {len(ctx)} 个片段并生成回答"}
            )
        else:
            steps.append(
                {"agent": "知识库 Agent", "desc": "知识库未命中，改用网络知识回答"}
            )
    steps.append({"agent": "统一回复渲染", "desc": "输出最终结果"})
    return steps

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    """接收用户输入，走多 Agent 工作流并返回结构化结果。"""
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    try:
        result = graph.invoke({"user_input": message})
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"执行失败：{e}") from e

    route = result.get("route", "unknown")
    return {
        "route": route,
        "answer": result.get("final_answer", ""),
        "trace": _build_trace(route, result),
        "plan": result.get("plan_json"),
        "source": result.get("rag_source"),
        "sources": result.get("rag_context") or [],
    }

@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """保存候选文档；只有用户随后确认导入时才写入知识索引。"""
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    prepared = []
    for f in files:
        name = os.path.basename(f.filename or "")
        if not name or name != (f.filename or "") or not name.lower().endswith(ALLOWED_EXT):
            raise HTTPException(status_code=400, detail=f"不支持的文件类型：{name}")
        prepared.append((f, name, _document_path(name)))
    saved = []
    for f, name, path in prepared:
        with open(path, "wb") as out:
            out.write(await f.read())
        saved.append(name)
    imported = get_imported_document_names()
    retained = [name for name in imported if name not in set(saved)]
    if retained != imported:
        state = _replace_imported_documents(retained)
    else:
        set_imported_document_names(imported)
        state = _knowledge_state()
    return {"saved": saved, **state}


@app.post("/api/reindex")
def reindex() -> Dict[str, Any]:
    """兼容旧地址：仅重建已经明确导入的文档。"""
    return _knowledge_state(_rebuild_documents())


@app.post("/api/documents/reimport")
def reimport_documents() -> Dict[str, Any]:
    """重新读取已导入文档并重建知识索引。"""
    return _knowledge_state(_rebuild_documents())


@app.post("/api/documents/{filename}/import")
def import_document(filename: str) -> Dict[str, Any]:
    """将候选文档加入知识库并重建索引。"""
    path = _document_path(filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文档不存在或已经删除")
    imported = get_imported_document_names()
    if filename not in imported:
        imported.append(filename)
    return {"imported": filename, **_replace_imported_documents(imported)}


@app.delete("/api/documents/{filename}/import")
def unimport_document(filename: str) -> Dict[str, Any]:
    """将文档移出知识库，但保留原文件供以后再次导入。"""
    imported = get_imported_document_names()
    if filename not in imported:
        raise HTTPException(status_code=404, detail="文档尚未导入知识库")
    return {
        "unimported": filename,
        **_replace_imported_documents([name for name in imported if name != filename]),
    }


@app.delete("/api/documents/{filename}")
def delete_document(filename: str) -> Dict[str, Any]:
    """永久删除单个源文档，并同步清除其向量数据。"""
    path = _document_path(filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文档不存在或已经删除")
    imported_before_delete = get_imported_document_names()
    try:
        os.remove(path)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"删除文档失败：{exc}") from exc
    if filename in imported_before_delete:
        state = _replace_imported_documents(
            [name for name in imported_before_delete if name != filename]
        )
    else:
        set_imported_document_names(imported_before_delete)
        state = _knowledge_state()
    return {"deleted": filename, **state}


@app.delete("/api/documents")
def clear_documents() -> Dict[str, Any]:
    """清空已导入清单并重置索引，保留源文档供以后重新导入。"""
    removed = get_imported_document_names()
    return {"removed": removed, **_replace_imported_documents([])}


@app.get("/api/status")
def status() -> Dict[str, Any]:
    """返回侧边栏所需的统计信息。"""
    init_db()
    overview = get_plan_overview()
    today = get_today_tasks()
    return {
        "plan": overview,
        **_knowledge_state(),
        "today_tasks": today,
        "follow_up_plans": get_follow_up_plans(),
    }


@app.get("/api/plan")
def full_plan() -> Dict[str, Any]:
    """兼容旧地址：返回全部学习计划及其多级任务数据。"""
    return get_full_plan()


@app.get("/api/plans")
def all_plans() -> Dict[str, Any]:
    """返回全部学习计划，供计划/周/日多级目录展示。"""
    return get_full_plan()


@app.delete("/api/plans/{plan_id}")
def remove_plan(plan_id: int) -> Dict[str, Any]:
    """删除指定学习计划及其任务。"""
    if plan_id <= 0 or not delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="学习计划不存在或已经删除")
    return {"deleted": plan_id, "plans": get_full_plan()}


@app.patch("/api/tasks/{task_id}")
def patch_task(task_id: int, req: TaskUpdateRequest) -> Dict[str, Any]:
    """勾选或取消任务；确认完成时要求提供 1-5 分评价。"""
    review = (req.review or "").strip()
    if len(review) > 500:
        raise HTTPException(status_code=400, detail="完成评价不能超过 500 个字符")
    if req.completed and (req.rating is None or not 1 <= req.rating <= 5):
        raise HTTPException(status_code=400, detail="确认完成前，请给本次学习 1-5 分评价")
    task = update_task(task_id, req.completed, req.rating, review)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已被新的计划替换")
    return {"task": task, "plan": get_plan_overview(task["plan_id"])}


@app.get("/api/checkins")
def checkin_calendar(month: str) -> Dict[str, Any]:
    """返回月度签到日历及今日签到资格。"""
    return get_checkins(_validate_month(month))


@app.post("/api/checkins")
def create_checkin() -> Dict[str, Any]:
    """完成全部今日任务后进行当天签到。"""
    result = check_in_today()
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return result


@app.post("/api/focus-sessions")
def create_focus_session(req: FocusSessionRequest) -> Dict[str, Any]:
    """保存一次计时专注记录。"""
    if not 1 <= req.duration_seconds <= 8 * 60 * 60:
        raise HTTPException(status_code=400, detail="专注时长必须在 1 秒到 8 小时之间")
    if req.mode not in {"focus", "break"}:
        raise HTTPException(status_code=400, detail="计时模式只能是 focus 或 break")
    task_name = (req.task_name or "").strip()
    if len(task_name) > 200:
        raise HTTPException(status_code=400, detail="专注事项不能超过 200 个字符")
    session = save_focus_session(
        req.duration_seconds, task_name, req.mode, req.completed, req.started_at
    )
    return {"session": session}


@app.get("/api/focus-sessions")
def focus_session_history(limit: int = 30) -> Dict[str, Any]:
    """返回专注页右侧使用的最近专注记录。"""
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="专注记录数量必须在 1 到 100 之间")
    sessions = get_focus_sessions(limit)
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/api/stats")
def learning_stats() -> Dict[str, Any]:
    """返回学习数据统计面板所需的聚合数据。"""
    return get_learning_stats()


def _normalize_course_time(value: str, label: str) -> str:
    match = re.fullmatch(r"\s*([01]?\d|2[0-3]):([0-5]\d)\s*", value or "")
    if not match:
        raise HTTPException(status_code=400, detail=f"{label}格式应为 HH:MM")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _validate_course_payload(req: CourseCreateRequest) -> Dict[str, Any]:
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="课程名称不能为空")
    if len(name) > 60:
        raise HTTPException(status_code=400, detail="课程名称不能超过 60 个字符")
    if not 1 <= req.day_of_week <= 7:
        raise HTTPException(status_code=400, detail="星期必须是 1（周一）到 7（周日）")
    start = _normalize_course_time(req.start_time, "开始时间")
    end = _normalize_course_time(req.end_time, "结束时间")
    if end <= start:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")
    return {
        "name": name,
        "day_of_week": req.day_of_week,
        "start_time": start,
        "end_time": end,
        "location": (req.location or "").strip()[:60],
        "teacher": (req.teacher or "").strip()[:30],
        "weeks_text": (req.weeks_text or "").strip()[:30],
    }


def _import_courses(parsed: List[Dict[str, Any]], source: str, import_url: str = "") -> Dict[str, Any]:
    count = replace_external_courses(parsed, source, import_url)
    return {"imported": count, **_course_state()}


def _course_state() -> Dict[str, Any]:
    state = get_courses()
    return {"courses": state["courses"], "import_url": state["import_url"], "count": len(state["courses"])}


@app.get("/api/courses")
def list_courses() -> Dict[str, Any]:
    """返回课表全部课程时段及上次导入链接。"""
    return _course_state()


@app.post("/api/courses")
def create_course(req: CourseCreateRequest) -> Dict[str, Any]:
    """手动新增一条课程时段。"""
    payload = _validate_course_payload(req)
    course = add_course(**payload)
    return {"course": course, **_course_state()}


@app.delete("/api/courses/{course_id}")
def remove_course(course_id: int) -> Dict[str, Any]:
    """删除单条课程时段。"""
    if course_id <= 0 or not delete_course(course_id):
        raise HTTPException(status_code=404, detail="课程不存在或已经删除")
    return {"deleted": course_id, **_course_state()}


@app.delete("/api/courses")
def clear_all_courses() -> Dict[str, Any]:
    """清空整张课表。"""
    removed = clear_courses()
    return {"removed": removed, **_course_state()}


@app.post("/api/courses/import-url")
def import_courses_by_url(req: CourseUrlImportRequest) -> Dict[str, Any]:
    """从 iCalendar 订阅链接导入课表，整体替换上次链接导入的课程。"""
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="请先粘贴课表订阅链接")
    if len(url) > 500:
        raise HTTPException(status_code=400, detail="链接过长，请确认是否粘贴正确")
    try:
        parsed = parse_ics(fetch_ics(url))
    except ICSParseError as exc:
        raise HTTPException(status_code=400, detail=f"课表导入失败：{exc}") from exc
    return _import_courses(parsed, "url", url)


@app.post("/api/courses/import-file")
async def import_courses_by_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传 .ics 文件导入课表，整体替换上次文件导入的课程。"""
    name = os.path.basename(file.filename or "")
    if not name.lower().endswith(".ics"):
        raise HTTPException(status_code=400, detail="请上传 .ics 格式的课表文件")
    payload = await file.read(2 * 1024 * 1024)
    text = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="课表文件编码无法识别")
    try:
        parsed = parse_ics(text)
    except ICSParseError as exc:
        raise HTTPException(status_code=400, detail=f"课表导入失败：{exc}") from exc
    return _import_courses(parsed, "file")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
