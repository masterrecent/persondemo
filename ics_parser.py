"""课表 ICS（iCalendar）解析：从订阅链接或 .ics 文件提取每周课程时段。"""
import re
import urllib.request
from datetime import datetime
from typing import Any, Dict, List

_WEEKDAY_MAP = {"MO": 1, "TU": 2, "WE": 3, "TH": 4, "FR": 5, "SA": 6, "SU": 7}


class ICSParseError(ValueError):
    """ICS 内容无法解析时抛出。"""


def fetch_ics(url: str, timeout: int = 15) -> str:
    """下载订阅链接的 ICS 文本；webcal:// 协议自动按 https:// 处理。"""
    url = (url or "").strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ICSParseError("链接必须以 http(s):// 或 webcal:// 开头")
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; ZhixuCourseImporter/1.0)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read(2 * 1024 * 1024)
            charset = response.headers.get_content_charset() or ""
    except OSError as exc:
        raise ICSParseError(f"无法访问该链接：{exc}") from exc
    for encoding in ([charset] if charset else []) + ["utf-8", "gb18030"]:
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ICSParseError("无法识别链接内容的文本编码")


def _unfold_lines(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape(value: str) -> str:
    return (
        value.replace("\\n", " ").replace("\\N", " ")
        .replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\").strip()
    )


def _parse_datetime(value: str) -> "datetime | None":
    value = value.strip().rstrip("Z").rstrip("z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None  # 纯日期（全天事件）按 None 处理，跳过


def _parse_rrule(value: str) -> Dict[str, str]:
    rule: Dict[str, str] = {}
    for part in value.split(";"):
        if "=" in part:
            key, item = part.split("=", 1)
            rule[key.strip().upper()] = item.strip()
    return rule


def _weeks_text(rule: Dict[str, str]) -> str:
    parts: List[str] = []
    until = rule.get("UNTIL", "")
    if until and len(until) >= 8:
        parts.append(f"至{until[:4]}-{until[4:6]}-{until[6:8]}")
    interval = rule.get("INTERVAL", "")
    if interval and interval != "1":
        parts.append(f"每{interval}周")
    return " ".join(parts)


def _build_event(props: Dict[str, str]) -> List[Dict[str, Any]]:
    start = _parse_datetime(props.get("DTSTART", ""))
    if start is None:
        return []
    end = _parse_datetime(props.get("DTEND", ""))
    if end is None:
        end = start.replace(hour=start.hour + 2)
    name = _unescape(props.get("SUMMARY", "")) or "未命名课程"
    rule = _parse_rrule(props.get("RRULE", ""))
    if rule.get("FREQ", "WEEKLY").upper() != "WEEKLY":
        return []  # 课表只关心每周重复的课程
    byday = [day.strip() for day in rule.get("BYDAY", "").split(",") if day.strip()]
    days = [_WEEKDAY_MAP[day[-2:].upper()] for day in byday if day[-2:].upper() in _WEEKDAY_MAP]
    if not days:
        days = [start.isoweekday()]
    weeks_text = _weeks_text(rule)
    courses = []
    for day in sorted(set(days)):
        courses.append(
            {
                "name": name[:60],
                "day_of_week": day,
                "start_time": start.strftime("%H:%M"),
                "end_time": end.strftime("%H:%M"),
                "location": _unescape(props.get("LOCATION", ""))[:60],
                "teacher": "",
                "weeks_text": weeks_text,
            }
        )
    return courses


def parse_ics(text: str) -> List[Dict[str, Any]]:
    """把 ICS 文本解析为课程时段列表；每个 VEVENT 按周几展开为多条。"""
    if "BEGIN:VCALENDAR" not in text or "BEGIN:VEVENT" not in text:
        raise ICSParseError("内容不是有效的 iCalendar（.ics）课表")
    courses: List[Dict[str, Any]] = []
    current: "Dict[str, str] | None" = None
    for line in _unfold_lines(text):
        stripped = line.strip("\x00").rstrip()
        if stripped == "BEGIN:VEVENT":
            current = {}
        elif stripped == "END:VEVENT":
            if current is not None:
                courses.extend(_build_event(current))
            current = None
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.split(";")[0].strip().upper()
            if key in {"SUMMARY", "LOCATION", "DTSTART", "DTEND", "RRULE"}:
                current[key] = value
    if not courses:
        raise ICSParseError("未在内容中找到任何带时间的课程事件（VEVENT）")
    courses.sort(key=lambda c: (c["day_of_week"], c["start_time"]))
    return courses
