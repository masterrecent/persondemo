"""SQLite 学习计划库：多计划、每日任务、完成状态与评价。"""
import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

DB_PATH = os.getenv("SQLITE_DB_PATH", "schedule.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _meta_value(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def init_db() -> None:
    """创建多计划结构，并将旧版单计划数据无损迁移到 plans 表。"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            source_prompt TEXT DEFAULT '',
            start_date TEXT NOT NULL,
            total_days INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER REFERENCES plans(id) ON DELETE CASCADE,
            day INTEGER NOT NULL,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            rating INTEGER,
            review TEXT DEFAULT '',
            completed_at TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS checkins (
            checkin_date TEXT PRIMARY KEY,
            total_tasks INTEGER NOT NULL,
            completed_tasks INTEGER NOT NULL,
            checked_at TEXT NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS focus_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT DEFAULT '',
            mode TEXT NOT NULL DEFAULT 'focus',
            duration_seconds INTEGER NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1,
            started_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT DEFAULT '',
            teacher TEXT DEFAULT '',
            weeks_text TEXT DEFAULT '',
            source TEXT DEFAULT 'manual',
            created_at TEXT NOT NULL
        )"""
    )
    existing_columns = {row["name"] for row in c.execute("PRAGMA table_info(tasks)")}
    migrations = {
        "plan_id": "ALTER TABLE tasks ADD COLUMN plan_id INTEGER REFERENCES plans(id) ON DELETE CASCADE",
        "rating": "ALTER TABLE tasks ADD COLUMN rating INTEGER",
        "review": "ALTER TABLE tasks ADD COLUMN review TEXT DEFAULT ''",
        "completed_at": "ALTER TABLE tasks ADD COLUMN completed_at TEXT",
    }
    for column, statement in migrations.items():
        if column not in existing_columns:
            c.execute(statement)

    orphan_count = c.execute(
        "SELECT COUNT(*) AS count FROM tasks WHERE plan_id IS NULL"
    ).fetchone()["count"]
    if orphan_count:
        start_date = _meta_value(conn, "start_date") or date.today().isoformat()
        goal = _meta_value(conn, "goal") or "历史学习计划"
        stored_days = _meta_value(conn, "total_days")
        max_day = c.execute(
            "SELECT COALESCE(MAX(day), 0) AS max_day FROM tasks WHERE plan_id IS NULL"
        ).fetchone()["max_day"]
        total_days = int(stored_days or max_day or 0)
        c.execute(
            """INSERT INTO plans (goal, source_prompt, start_date, total_days, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (goal, "由旧版单计划数据迁移", start_date, total_days, datetime.now().isoformat(timespec="seconds")),
        )
        legacy_plan_id = c.lastrowid
        c.execute("UPDATE tasks SET plan_id=? WHERE plan_id IS NULL", (legacy_plan_id,))
        _set_meta(conn, "latest_plan_id", str(legacy_plan_id))

    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_plan_day ON tasks(plan_id, day)")
    conn.commit()
    conn.close()


def _current_day(start_date: Optional[str]) -> int:
    if not start_date:
        return 0
    try:
        return (date.today() - date.fromisoformat(start_date)).days + 1
    except ValueError:
        return 0


def _plan_summary(row: sqlite3.Row) -> Dict[str, Any]:
    total_tasks = int(row["total_tasks"] or 0)
    completed_tasks = int(row["completed_tasks"] or 0)
    total_days = int(row["total_days"] or row["max_day"] or 0)
    start_date = row["start_date"]
    end_date = None
    try:
        end_date = (date.fromisoformat(start_date) + timedelta(days=max(total_days - 1, 0))).isoformat()
    except (TypeError, ValueError):
        pass
    return {
        "id": row["id"],
        "goal": row["goal"],
        "source_prompt": row["source_prompt"],
        "start_date": start_date,
        "end_date": end_date,
        "created_at": row["created_at"],
        "total_days": total_days,
        "current_day": _current_day(start_date),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress": round(completed_tasks * 100 / total_tasks) if total_tasks else 0,
    }


def _plan_query(where: str = "", params: tuple = ()) -> List[sqlite3.Row]:
    conn = _get_conn()
    rows = conn.execute(
        f"""SELECT p.id, p.goal, p.source_prompt, p.start_date, p.total_days,
                   p.created_at, COUNT(t.id) AS total_tasks,
                   SUM(CASE WHEN t.status='completed' THEN 1 ELSE 0 END) AS completed_tasks,
                   MAX(t.day) AS max_day
            FROM plans p LEFT JOIN tasks t ON t.plan_id=p.id
            {where}
            GROUP BY p.id
            ORDER BY p.created_at DESC, p.id DESC""",
        params,
    ).fetchall()
    conn.close()
    return rows


def save_plan(
    plan_json: Dict[str, Any], start_date: str | None = None, source_prompt: str = ""
) -> Dict[str, int]:
    """新增一条学习计划。不同规划提问会保留为不同计划，不覆盖历史数据。"""
    init_db()
    start_date = start_date or date.today().isoformat()
    tasks = plan_json.get("tasks", [])
    goal = str(plan_json.get("goal") or source_prompt or "我的学习计划")
    total_days = int(plan_json.get("total_days") or max((int(t.get("day", 0)) for t in tasks), default=0))
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO plans (goal, source_prompt, start_date, total_days, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (goal, source_prompt.strip(), start_date, total_days, datetime.now().isoformat(timespec="seconds")),
    )
    plan_id = int(c.lastrowid)
    for task in tasks:
        c.execute(
            """INSERT INTO tasks (plan_id, day, topic, content)
               VALUES (?, ?, ?, ?)""",
            (plan_id, int(task["day"]), str(task["topic"]), str(task["content"])),
        )
    _set_meta(conn, "latest_plan_id", str(plan_id))
    conn.commit()
    conn.close()
    return {"plan_id": plan_id, "count": len(tasks)}


def get_plan_overview(plan_id: Optional[int] = None) -> Dict[str, Any]:
    """返回指定计划概览；未指定时返回最近创建的计划。"""
    init_db()
    if plan_id is None:
        rows = _plan_query()
    else:
        rows = _plan_query("WHERE p.id=?", (plan_id,))
    if not rows:
        return {
            "id": None, "goal": "", "start_date": None, "end_date": None,
            "total_days": 0, "current_day": 0, "total_tasks": 0,
            "completed_tasks": 0, "progress": 0,
        }
    return _plan_summary(rows[0])


def get_today_tasks() -> List[Dict[str, Any]]:
    """返回所有计划在今天对应的任务，供独立今日安排页集中执行。"""
    init_db()
    conn = _get_conn()
    plans = conn.execute("SELECT id, goal, start_date FROM plans ORDER BY created_at DESC, id DESC").fetchall()
    tasks: List[Dict[str, Any]] = []
    for plan in plans:
        day_num = _current_day(plan["start_date"])
        if day_num <= 0:
            continue
        rows = conn.execute(
            """SELECT id, plan_id, day, topic, content, status, rating, review, completed_at
               FROM tasks WHERE plan_id=? AND day=? ORDER BY id""",
            (plan["id"], day_num),
        ).fetchall()
        for row in rows:
            task = dict(row)
            task["plan_goal"] = plan["goal"]
            task["scheduled_date"] = date.today().isoformat()
            tasks.append(task)
    conn.close()
    return tasks


def get_all_plans() -> Dict[str, Any]:
    """返回全部计划及任务，前端据此渲染计划/周/日多级只读目录。"""
    init_db()
    summaries = [_plan_summary(row) for row in _plan_query()]
    conn = _get_conn()
    for plan in summaries:
        rows = conn.execute(
            """SELECT id, plan_id, day, topic, content, status, rating, review, completed_at
               FROM tasks WHERE plan_id=? ORDER BY day, id""",
            (plan["id"],),
        ).fetchall()
        try:
            start = date.fromisoformat(plan["start_date"])
        except (TypeError, ValueError):
            start = date.today()
        plan["tasks"] = []
        for row in rows:
            task = dict(row)
            task["scheduled_date"] = (start + timedelta(days=task["day"] - 1)).isoformat()
            plan["tasks"].append(task)
    conn.close()
    total_tasks = sum(plan["total_tasks"] for plan in summaries)
    completed_tasks = sum(plan["completed_tasks"] for plan in summaries)
    return {
        "plans": summaries,
        "plan_count": len(summaries),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress": round(completed_tasks * 100 / total_tasks) if total_tasks else 0,
    }


def get_follow_up_plans() -> List[Dict[str, Any]]:
    """返回仍有未完成任务的计划及各自下一项可学习内容。"""
    init_db()
    summaries = [_plan_summary(row) for row in _plan_query()]
    conn = _get_conn()
    results: List[Dict[str, Any]] = []
    for plan in summaries:
        if plan["completed_tasks"] >= plan["total_tasks"]:
            continue
        next_task = conn.execute(
            """SELECT id, plan_id, day, topic, content, status
               FROM tasks
               WHERE plan_id=? AND status!='completed' AND day>?
               ORDER BY day, id LIMIT 1""",
            (plan["id"], max(int(plan["current_day"] or 0), 0)),
        ).fetchone()
        if next_task is None:
            next_task = conn.execute(
                """SELECT id, plan_id, day, topic, content, status
                   FROM tasks
                   WHERE plan_id=? AND status!='completed'
                   ORDER BY day, id LIMIT 1""",
                (plan["id"],),
            ).fetchone()
        if next_task is None:
            continue
        task = dict(next_task)
        try:
            start = date.fromisoformat(plan["start_date"])
            task["scheduled_date"] = (start + timedelta(days=task["day"] - 1)).isoformat()
        except (TypeError, ValueError):
            task["scheduled_date"] = None
        results.append({**plan, "next_task": task})
    conn.close()
    return results


def delete_plan(plan_id: int) -> bool:
    """删除一条学习计划；关联任务由外键级联删除。"""
    init_db()
    conn = _get_conn()
    exists = conn.execute("SELECT 1 FROM plans WHERE id=?", (plan_id,)).fetchone()
    if not exists:
        conn.close()
        return False
    conn.execute("DELETE FROM plans WHERE id=?", (plan_id,))
    if _meta_value(conn, "latest_plan_id") == str(plan_id):
        latest = conn.execute(
            "SELECT id FROM plans ORDER BY created_at DESC, id DESC LIMIT 1"
        ).fetchone()
        if latest:
            _set_meta(conn, "latest_plan_id", str(latest["id"]))
        else:
            conn.execute("DELETE FROM meta WHERE key='latest_plan_id'")
    conn.commit()
    conn.close()
    return True


def get_full_plan() -> Dict[str, Any]:
    """兼容旧接口名称，返回新的多计划集合。"""
    return get_all_plans()


def update_task(
    task_id: int, completed: bool, rating: Optional[int] = None, review: str = ""
) -> Optional[Dict[str, Any]]:
    """更新今日任务的完成状态与评价。"""
    init_db()
    conn = _get_conn()
    row = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return None
    if completed:
        conn.execute(
            """UPDATE tasks SET status='completed', rating=?, review=?, completed_at=?
               WHERE id=?""",
            (rating, review.strip(), datetime.now().isoformat(timespec="seconds"), task_id),
        )
    else:
        conn.execute(
            """UPDATE tasks SET status='pending', rating=NULL, review='', completed_at=NULL
               WHERE id=?""",
            (task_id,),
        )
    conn.commit()
    result = conn.execute(
        """SELECT id, plan_id, day, topic, content, status, rating, review, completed_at
           FROM tasks WHERE id=?""",
        (task_id,),
    ).fetchone()
    conn.close()
    return dict(result) if result else None


def get_checkins(month: str) -> Dict[str, Any]:
    """返回指定月份签到记录，以及今天是否满足签到条件。"""
    init_db()
    conn = _get_conn()
    rows = conn.execute(
        """SELECT checkin_date, total_tasks, completed_tasks, checked_at
           FROM checkins WHERE checkin_date LIKE ? ORDER BY checkin_date""",
        (f"{month}-%",),
    ).fetchall()
    all_rows = conn.execute(
        "SELECT checkin_date FROM checkins ORDER BY checkin_date DESC"
    ).fetchall()
    conn.close()
    today_tasks = get_today_tasks()
    completed = sum(task["status"] == "completed" for task in today_tasks)
    today_value = date.today().isoformat()
    dates = {row["checkin_date"] for row in all_rows}
    streak = 0
    cursor = date.today()
    while cursor.isoformat() in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "month": month,
        "records": [dict(row) for row in rows],
        "today": today_value,
        "today_checked": today_value in dates,
        "eligible": bool(today_tasks) and completed == len(today_tasks),
        "today_total": len(today_tasks),
        "today_completed": completed,
        "streak": streak,
    }


def check_in_today() -> Dict[str, Any]:
    """当且仅当今日全部任务完成时写入签到记录。"""
    init_db()
    tasks = get_today_tasks()
    completed = sum(task["status"] == "completed" for task in tasks)
    if not tasks:
        return {"ok": False, "reason": "今天没有学习任务，暂时无需签到"}
    if completed != len(tasks):
        return {
            "ok": False,
            "reason": f"完成全部今日任务后才能签到（{completed}/{len(tasks)}）",
        }
    today_value = date.today().isoformat()
    conn = _get_conn()
    already_checked = bool(
        conn.execute(
            "SELECT 1 FROM checkins WHERE checkin_date=?", (today_value,)
        ).fetchone()
    )
    conn.execute(
        """INSERT INTO checkins (checkin_date, total_tasks, completed_tasks, checked_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(checkin_date) DO NOTHING""",
        (today_value, len(tasks), completed, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "checkin_date": today_value, "already_checked": already_checked}


def save_focus_session(
    duration_seconds: int,
    task_name: str = "",
    mode: str = "focus",
    completed: bool = True,
    started_at: Optional[str] = None,
) -> Dict[str, Any]:
    """保存一次专注或休息记录，返回新记录。"""
    init_db()
    timestamp = started_at or datetime.now().isoformat(timespec="seconds")
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO focus_sessions
           (task_name, mode, duration_seconds, completed, started_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            task_name.strip(), mode, int(duration_seconds), int(completed), timestamp,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    session_id = int(cursor.lastrowid)
    conn.commit()
    row = conn.execute("SELECT * FROM focus_sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row)


def get_focus_sessions(limit: int = 30) -> List[Dict[str, Any]]:
    """按时间倒序返回最近的正式专注记录，不包含休息计时。"""
    init_db()
    conn = _get_conn()
    rows = conn.execute(
        """SELECT id, task_name, duration_seconds, completed, started_at, created_at
           FROM focus_sessions
           WHERE mode='focus'
           ORDER BY created_at DESC, id DESC
           LIMIT ?""",
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_learning_stats() -> Dict[str, Any]:
    """聚合专注、任务、自评、计划和签到数据。"""
    init_db()
    today = date.today()
    first_day = today - timedelta(days=6)
    conn = _get_conn()
    focus_rows = conn.execute(
        """SELECT substr(started_at, 1, 10) AS session_date,
                  SUM(duration_seconds) AS seconds, COUNT(*) AS sessions
           FROM focus_sessions
           WHERE mode='focus' AND substr(started_at, 1, 10) BETWEEN ? AND ?
           GROUP BY substr(started_at, 1, 10)""",
        (first_day.isoformat(), today.isoformat()),
    ).fetchall()
    focus_map = {row["session_date"]: dict(row) for row in focus_rows}
    daily = []
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for offset in range(7):
        current = first_day + timedelta(days=offset)
        record = focus_map.get(current.isoformat(), {})
        seconds = int(record.get("seconds") or 0)
        daily.append(
            {
                "date": current.isoformat(),
                "label": weekday_names[current.weekday()],
                "seconds": seconds,
                "minutes": round(seconds / 60),
                "sessions": int(record.get("sessions") or 0),
            }
        )

    all_focus = conn.execute(
        """SELECT COALESCE(SUM(duration_seconds), 0) AS seconds, COUNT(*) AS sessions
           FROM focus_sessions WHERE mode='focus'"""
    ).fetchone()
    task_stats = conn.execute(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
                  AVG(CASE WHEN status='completed' THEN rating END) AS avg_rating
           FROM tasks"""
    ).fetchone()
    plan_count = conn.execute("SELECT COUNT(*) AS count FROM plans").fetchone()["count"]
    checkin_rows = conn.execute(
        "SELECT checkin_date FROM checkins ORDER BY checkin_date DESC"
    ).fetchall()
    conn.close()

    checkin_dates = {row["checkin_date"] for row in checkin_rows}
    streak = 0
    cursor_date = today
    while cursor_date.isoformat() in checkin_dates:
        streak += 1
        cursor_date -= timedelta(days=1)
    total_tasks = int(task_stats["total"] or 0)
    completed_tasks = int(task_stats["completed"] or 0)
    return {
        "today_focus_seconds": daily[-1]["seconds"],
        "week_focus_seconds": sum(item["seconds"] for item in daily),
        "total_focus_seconds": int(all_focus["seconds"] or 0),
        "total_sessions": int(all_focus["sessions"] or 0),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "task_completion": round(completed_tasks * 100 / total_tasks) if total_tasks else 0,
        "average_rating": round(float(task_stats["avg_rating"] or 0), 1),
        "plan_count": int(plan_count or 0),
        "checkin_streak": streak,
        "daily": daily,
    }


def get_courses() -> Dict[str, Any]:
    """返回课表中的全部课程时段及上次使用的导入链接。"""
    init_db()
    conn = _get_conn()
    rows = conn.execute(
        """SELECT id, name, day_of_week, start_time, end_time, location, teacher,
                  weeks_text, source, created_at
           FROM courses ORDER BY day_of_week, start_time, id"""
    ).fetchall()
    import_url = _meta_value(conn, "course_import_url") or ""
    conn.close()
    return {"courses": [dict(row) for row in rows], "import_url": import_url}


def add_course(
    name: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    location: str = "",
    teacher: str = "",
    weeks_text: str = "",
) -> Dict[str, Any]:
    """手动新增一条课程时段。"""
    init_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO courses (name, day_of_week, start_time, end_time, location,
                                teacher, weeks_text, source, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?)""",
        (
            name.strip(), day_of_week, start_time, end_time,
            location.strip(), teacher.strip(), weeks_text.strip(),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    course_id = int(c.lastrowid)
    row = conn.execute(
        """SELECT id, name, day_of_week, start_time, end_time, location, teacher,
                  weeks_text, source, created_at FROM courses WHERE id=?""",
        (course_id,),
    ).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


def delete_course(course_id: int) -> bool:
    """删除单条课程时段；返回是否删除了记录。"""
    init_db()
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def clear_courses() -> int:
    """清空课表并忘记导入链接；返回删除的课程数。"""
    init_db()
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"]
    conn.execute("DELETE FROM courses")
    _set_meta(conn, "course_import_url", "")
    conn.commit()
    conn.close()
    return int(count or 0)


def replace_external_courses(
    courses: List[Dict[str, Any]], source: str, import_url: str = ""
) -> int:
    """用一次导入的结果整体替换同一来源的课程；手动添加的课程不受影响。"""
    init_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM courses WHERE source=?", (source,))
    for course in courses:
        c.execute(
            """INSERT INTO courses (name, day_of_week, start_time, end_time, location,
                                    teacher, weeks_text, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(course["name"]).strip(),
                int(course["day_of_week"]),
                course["start_time"],
                course["end_time"],
                str(course.get("location", "")).strip(),
                str(course.get("teacher", "")).strip(),
                str(course.get("weeks_text", "")).strip(),
                source,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
    _set_meta(conn, "course_import_url", import_url)
    conn.commit()
    conn.close()
    return len(courses)
