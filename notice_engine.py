"""Small, deterministic retrieval layer for the demo notice collection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

NOTICE_PATH = Path(__file__).with_name("notices.json")
CHINA_TZ = timezone(timedelta(hours=8))
MISSING = "当前收录的通知未说明该信息，建议查看原始通知或向活动组织方核实。"
DEMO = "模拟通知，仅用于赛事功能演示，非真实校园公告。"


@dataclass
class Answer:
    text: str
    evidence: list[dict[str, Any]]
    kind: str = "detail"


def load_notices(path: Path = NOTICE_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        notices = json.load(handle)
    ids = [item["id"] for item in notices]
    if len(ids) != len(set(ids)):
        raise ValueError("通知编号重复")
    for item in notices:
        if DEMO not in item["original_text"]:
            raise ValueError(f"通知 {item['id']} 缺少模拟标记")
        datetime.fromisoformat(item["registration_deadline"])
        if item.get("updated_from") and item["updated_from"] not in ids:
            raise ValueError(f"通知 {item['id']} 的更新关系无效")
    return notices


def current_notices(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only an explicit updated_from relation supersedes an old notice."""
    replaced = {n["updated_from"] for n in notices if n.get("updated_from")}
    return [n for n in notices if n["id"] not in replaced]


def deadline(notice: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(notice["registration_deadline"]).replace(tzinfo=CHINA_TZ)


def status(notice: dict[str, Any], now: datetime) -> str:
    return "已截止 · 历史信息" if deadline(notice) < now else "报名中"


def sorted_by_deadline(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(notices, key=deadline)


def _normalize(value: str) -> str:
    return re.sub(r"[\s·（）()《》:：，,。！？?、\-]", "", value).lower()


def _query_category(question: str) -> str | None:
    if any(token in question for token in ("比赛", "竞赛", "建模", "赛事")):
        return "学科竞赛"
    if "讲座" in question:
        return "学术讲座"
    if "志愿" in question:
        return "志愿服务"
    if any(token in question for token in ("英语", "交流")):
        return "英语交流活动"
    if "文化节" in question:
        return "校园活动"
    return None


def select_notices(
    question: str, notices: list[dict[str, Any]], category_filter: str = "全部"
) -> list[dict[str, Any]]:
    active = current_notices(notices)
    if category_filter != "全部":
        active = [n for n in active if n["category"] == category_filter]
    normalized = _normalize(question)
    by_id = [n for n in active if n["id"].lower() in normalized]
    if by_id:
        return by_id
    alias_hits: list[tuple[int, dict[str, Any]]] = []
    for notice in active:
        names = [notice["title"]] + notice.get("aliases", [])
        lengths = [len(_normalize(name)) for name in names if _normalize(name) in normalized]
        if lengths:
            alias_hits.append((max(lengths), notice))
    if alias_hits:
        best = max(score for score, _ in alias_hits)
        return [item for score, item in alias_hits if score == best]
    query_category = _query_category(question)
    if query_category:
        return [n for n in active if n["category"] == query_category]
    if any(word in question for word in ("所有活动", "哪些活动", "全部通知", "所有通知", "最近活动", "快截止", "截止时间", "报名截止")):
        return active
    return []


def _field(notice: dict[str, Any], key: str) -> str:
    value = notice.get(key)
    if value is None or value == "" or value == []:
        return MISSING
    return "、".join(value) if isinstance(value, list) else str(value)


def _change_lines(new: dict[str, Any], notices: list[dict[str, Any]]) -> list[str]:
    old = next((n for n in notices if n["id"] == new.get("updated_from")), None)
    if not old:
        return ["当前收录数据未记录这条通知的明确更新关系。"]
    names = {"event_time": "活动时间", "registration_deadline": "报名截止时间", "location": "活动地点", "materials": "报名材料", "registration_entry": "报名入口"}
    lines = [f"**版本关系：** {old['id']} → {new['id']}（确认更新）"]
    for key, label in names.items():
        if old.get(key) != new.get(key):
            lines.append(f"- {label}：{_field(old, key)} → **{_field(new, key)}**")
    if len(lines) == 1:
        lines.append("- 两版收录字段没有差异。")
    return lines


def build_answer(
    question: str,
    notices: list[dict[str, Any]],
    now: datetime | None = None,
    category_filter: str = "全部",
) -> Answer:
    now = now or datetime.now(CHINA_TZ)
    chosen = select_notices(question, notices, category_filter)
    if not chosen:
        return Answer("在当前收录的模拟通知中未找到与这个问题相关的资料。请尝试活动名称、类别或通知编号。", [], "none")

    q = question.strip()
    is_fee = any(x in q for x in ("费用", "收费", "多少钱", "免费"))
    is_update = any(x in q for x in ("更新", "改期", "变更", "最新版", "最新截止"))
    is_source = any(x in q for x in ("原文", "出处", "来源", "依据"))
    is_place = any(x in q for x in ("哪里", "地点", "在哪"))
    is_material = any(x in q for x in ("材料", "准备", "报名要求", "参赛要求", "条件"))
    is_deadline = any(x in q for x in ("截止", "排序", "从早到晚"))
    is_entry = any(x in q for x in ("入口", "链接", "网址", "怎么报名"))

    if len(chosen) > 1:
        arranged = sorted_by_deadline(chosen) if is_deadline else sorted(chosen, key=lambda n: n["published_at"], reverse=True)
        header = "按报名截止时间从早到晚排列：" if is_deadline else "找到以下相关通知："
        lines = [header, "", "| 通知 | 类别 | 报名截止 | 状态 | 来源 |", "|---|---|---|---|---|"]
        for n in arranged:
            lines.append(f"| {n['title']}（{n['id']}） | {n['category']} | {n['registration_deadline']} | {status(n, now)} | {n['source']} |")
        lines.append("\n每条通知的原文可在下方“来源与通知原文”展开核对。")
        return Answer("\n".join(lines), arranged, "list")

    n = chosen[0]
    lines = [f"### {n['title']} · {n['id']}", f"**状态：{status(n, now)}**"]
    if is_fee:
        lines.append(f"报名费用：{_field(n, 'registration_fee')}")
    elif is_update:
        lines += _change_lines(n, notices)
        lines.append(f"**当前报名截止时间：{_field(n, 'registration_deadline')}**")
    elif is_place:
        lines.append(f"活动地点：{_field(n, 'location')}")
        lines.append(f"活动时间：{_field(n, 'event_time')}")
    elif is_material:
        lines.append(f"适用对象：{_field(n, 'audience')}")
        lines.append(f"报名材料：{_field(n, 'materials')}")
    elif is_entry:
        lines.append(f"报名入口：{_field(n, 'registration_entry')}")
    elif is_deadline:
        lines.append(f"报名截止时间：**{_field(n, 'registration_deadline')}**")
    elif is_source:
        lines.append(f"信息来源：{n['source']}")
    else:
        lines += [f"类别：{n['category']}", f"适用对象：{_field(n, 'audience')}", f"活动时间：{_field(n, 'event_time')}", f"活动地点：{_field(n, 'location')}", f"报名截止时间：{_field(n, 'registration_deadline')}", f"报名材料：{_field(n, 'materials')}", f"报名入口：{_field(n, 'registration_entry')}"]
    lines += [f"\n**来源：**{n['source']} · {n['id']} · 版本 {n['version']}", "**相关原文：**", f"> {n['original_text']}"]
    return Answer("\n\n".join(lines), [n])
