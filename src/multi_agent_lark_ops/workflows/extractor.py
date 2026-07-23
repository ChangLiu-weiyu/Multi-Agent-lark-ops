"""Extract actionable work items from Lark document text."""

from __future__ import annotations

import re

from multi_agent_lark_ops.state import WorkItem

_TASK_MARKER = re.compile(r"^(?:[-*]\s+|\d+[.、]\s*)(?P<title>.+)$")
_HEADING_MARKER = re.compile(r"^#{1,6}\s*(?P<title>.+)$")
_GROUP_MARKER = re.compile(r"^(?P<group>[\w\u4e00-\u9fff、/ +＋&（）()]+?)(?:部门|组|两部门)?[:：]$")

_TASK_SECTION_HINTS = ("近期待办", "紧急重要", "todo", "to-do")
_SKIP_PREFIXES = ("|", "<", ">")
_STOP_LINES = ("---",)
_STOP_PREFIXES = ("来源<", "文档生成时间")


def _clean_line(line: str) -> str:
    return line.strip().strip("\ufeff")


def _is_task_section_title(line: str) -> bool:
    lowered = line.lower()
    return any(hint in lowered for hint in _TASK_SECTION_HINTS)


def _heading_title(line: str) -> str | None:
    match = _HEADING_MARKER.match(line)
    if not match:
        return None
    return match.group("title").strip()


def _is_group_label(line: str) -> bool:
    if len(line) > 30:
        return False
    return bool(_GROUP_MARKER.match(line))


def _strip_group_suffix(line: str) -> str:
    return line.rstrip(":：").strip()


def _append_detail(item: WorkItem, extra: str) -> WorkItem:
    detail = f"{item.detail}\n{extra}" if item.detail else extra
    return WorkItem(title=item.title, detail=detail, source=item.source, assigned_role=item.assigned_role)


def _should_stop_task_section(line: str) -> bool:
    return line in _STOP_LINES or any(line.startswith(prefix) for prefix in _STOP_PREFIXES)


def extract_work_items(document_text: str, *, source: str = "lark-doc") -> list[WorkItem]:
    """Extract numbered or bulleted action items from task-oriented sections.

    The first milestone is intentionally conservative: it focuses on task sections
    such as "近期待办" so role descriptions do not become noisy work items.
    """

    work_items: list[WorkItem] = []
    in_task_section = False
    current_group = ""
    last_index: int | None = None

    for raw_line in document_text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue

        heading = _heading_title(line)
        if heading is not None:
            in_task_section = _is_task_section_title(heading)
            current_group = ""
            last_index = None
            continue

        if not in_task_section and _is_task_section_title(line):
            in_task_section = True
            current_group = ""
            last_index = None
            continue

        if not in_task_section:
            continue

        if _should_stop_task_section(line):
            in_task_section = False
            current_group = ""
            last_index = None
            continue

        if line.startswith(_SKIP_PREFIXES):
            continue

        if _is_group_label(line):
            current_group = _strip_group_suffix(line)
            last_index = None
            continue

        task_match = _TASK_MARKER.match(line)
        if task_match:
            title = task_match.group("title").strip()
            detail = f"部门/上下文：{current_group}" if current_group else ""
            work_items.append(WorkItem(title=title, detail=detail, source=source))
            last_index = len(work_items) - 1
            continue

        if last_index is not None:
            work_items[last_index] = _append_detail(work_items[last_index], line)

    return work_items
